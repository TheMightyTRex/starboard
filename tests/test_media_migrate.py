"""Moving to another media server (DASH-587): what is read from both servers, what is carried across, and in what order.
The three servers are answered by one stateful stand-in written from each server's documented API (no real Plex, Emby or
Jellyfin is asked), so what was added and marked can be read back. Run once against a real server of each kind before a
release: Settings, Apps, the media server tab, Switch with help."""
import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from unittest import mock

import http.client

from starboard import auth, media_migrate as mm, mediaserver, migrate, plugins_admin as pa, server, services

JF = {"id": "jf", "name": "Jellyfin", "type": "jellyfin", "url": "http://jf:8096", "api_key": "jk", "enabled": True}
EMBY = {"id": "emby", "name": "Emby", "type": "emby", "url": "http://emby:8096", "api_key": "ek", "enabled": True}
PLEX = {"id": "plex", "name": "Plex", "type": "plex", "url": "http://plex:32400", "api_key": "pt", "enabled": True}


class Server:
    """A Jellyfin or Emby: libraries, people, items with each person's watched state."""

    def __init__(self, libs=(), users=(), items=(), prefix=""):
        self.prefix = prefix
        self.libs = [dict(x) for x in libs]
        self.users = [{"Id": f"u-{n.lower()}", "Name": n, "Policy": {"IsAdministrator": n == "Sam"}} for n in users]
        self.items = items
        self.state = {}  # (user id, item id) -> UserData
        self.calls, self.passwords = [], {}

    def user_data(self, uid, item_id):
        return self.state.setdefault((uid, item_id), {"Played": False, "PlaybackPositionTicks": 0})

    def handle(self, method, route, q, body):
        self.calls.append((method, route))
        if route == "/System/Info":
            return {"Version": "10.11.0", "ServerName": "Den"}
        if route == "/Library/VirtualFolders" and method == "GET":
            return [{"Name": x["Name"], "CollectionType": x.get("CollectionType"), "Locations": x["Locations"], "ItemId": x["Name"]} for x in self.libs]
        if route == "/Library/VirtualFolders" and method == "POST":
            if any(not p["Path"].startswith("/data/media") for p in body["LibraryOptions"]["PathInfos"]):
                raise services.ServiceError("Jellyfin answered with error 400")
            self.libs.append({"Name": q["name"], "CollectionType": q.get("collectionType"), "Locations": [p["Path"] for p in body["LibraryOptions"]["PathInfos"]]})
            return ""
        if route == "/Library/Refresh":
            return ""
        if route == "/Users" and method == "GET":
            return self.users
        if route == "/Users/New":
            if any(u["Name"].lower() == body["Name"].lower() for u in self.users):
                raise services.ServiceError("answered with error 400")
            uid = f"u-{body['Name'].lower()}"
            self.users.append({"Id": uid, "Name": body["Name"], "Policy": {}})
            if body.get("Password"):
                self.passwords[uid] = body["Password"]
            return {"Id": uid, "Name": body["Name"]}
        if route.endswith("/Password"):
            self.passwords[route.split("/")[2]] = body["NewPw"]
            return ""
        uid = (route.split("/")[2] if route.startswith("/Users/") else q.get("userId") or q.get("UserId") or "")
        if route.endswith("/Items") or route == "/Items":
            wanted = {i for i in (q.get("Ids") or q.get("ids") or "").split(",") if i}
            flt = q.get("Filters", "")
            out = []
            for it in self.items:
                ud = self.user_data(uid, it["Id"]) if uid else {}
                if wanted and it["Id"] not in wanted:
                    continue
                if not wanted and "IncludeItemTypes" in {k.title() if k != "includeItemTypes" else "IncludeItemTypes" for k in q} and it["Type"] not in (q.get("IncludeItemTypes") or q.get("includeItemTypes") or "").split(","):
                    continue
                if flt == "IsPlayed" and not ud.get("Played"):
                    continue
                if flt == "IsResumable" and not ud.get("PlaybackPositionTicks"):
                    continue
                out.append({**it, "UserData": dict(ud)})
            if q.get("limit") == "1":
                out = out[:1]
            return {"Items": out, "TotalRecordCount": len(out)}
        if route.startswith("/Users/") and "/PlayedItems/" in route:
            self.user_data(route.split("/")[2], route.split("/")[4])["Played"] = True
            return ""
        if route.startswith("/UserPlayedItems/"):
            self.user_data(uid, route.split("/")[2])["Played"] = True
            return ""
        if route.endswith("/UserData"):
            parts = route.split("/")
            self.user_data(parts[2] if parts[1] == "Users" else uid, parts[4] if parts[1] == "Users" else parts[2])["PlaybackPositionTicks"] = body["PlaybackPositionTicks"]
            return ""
        raise AssertionError(f"not answered: {method} {route}")


class PlexServer:
    def __init__(self, libs=(), people=("Owner",), watched=(), seen=True):
        self.seen = seen  # False: a new server, nothing watched in it yet
        self.libs = [dict(x) for x in libs]
        self.people = people
        self.watched = list(watched)  # (kind, key)
        self.calls = []
        self.progress = []

    MOVIES = [{"ratingKey": "10", "title": "Dune", "year": 2021, "Guid": [{"id": "tmdb://438631"}], "viewCount": 2, "lastViewedAt": 1700000000, "duration": 9000000, "type": "movie"},
              {"ratingKey": "11", "title": "Arrival", "year": 2016, "Guid": [{"id": "tmdb://329865"}], "viewOffset": 600000, "duration": 6000000, "type": "movie"}]
    SHOWS = [{"ratingKey": "20", "title": "Harbour", "year": 2020, "Guid": [{"id": "tvdb://111"}]}]
    EPISODES = [{"ratingKey": "21", "title": "Pilot", "grandparentTitle": "Harbour", "grandparentRatingKey": "20", "parentIndex": 1, "index": 1, "viewCount": 1, "lastViewedAt": 1700000100, "duration": 100}]

    def handle(self, method, route, q, body):
        self.calls.append((method, route + ("?" + urllib.parse.urlencode(q) if q else "")))
        if route == "/":
            return {"MediaContainer": {"friendlyName": "Den", "version": "1.41.3.9314-x"}}
        if route == "/myplex/account":
            return {"MediaContainer": {"username": "Sam"}}
        if route == "/accounts":
            return {"MediaContainer": {"Account": [{"id": 0, "name": ""}] + [{"id": n + 1, "name": p} for n, p in enumerate(self.people)]}}
        if route == "/library/sections" and method == "GET":
            return {"MediaContainer": {"Directory": [{"key": str(n + 1), "title": x["title"], "type": x["type"], "Location": [{"path": p} for p in x["paths"]]} for n, x in enumerate(self.libs)]}}
        if route == "/library/sections" and method == "POST":
            self.libs.append({"title": q["name"], "type": q["type"], "paths": [q["location"]], "agent": q["agent"], "scanner": q["scanner"]})
            return "<MediaContainer/>"
        if route == "/library/sections/all/refresh":
            return ""
        if route.startswith("/library/sections/") and route.endswith("/all"):
            kind = q.get("type")
            rows = {"1": self.MOVIES, "2": self.SHOWS, "4": self.EPISODES}[kind]
            if not self.seen:
                rows = [{k: v for k, v in r.items() if k not in ("viewCount", "viewOffset")} for r in rows]
            return {"MediaContainer": {"Metadata": rows}}
        if route == "/:/scrobble":
            self.watched.append(q["key"])
            return ""
        if route == "/:/progress":
            self.progress.append((q["key"], q["time"]))
            return ""
        raise AssertionError(f"not answered: {method} {route}")


class World:
    """services._fetch for three servers by address; remembers what each was asked."""

    def __init__(self, **by_host):
        self.by_host = by_host

    def __call__(self, service, req, timeout):
        u = urllib.parse.urlsplit(req.full_url)
        server = self.by_host[u.hostname]
        route = u.path[len(server.prefix):] if getattr(server, "prefix", "") and u.path.startswith(server.prefix) else u.path
        q = dict(urllib.parse.parse_qsl(u.query))
        if isinstance(server, PlexServer):
            q = dict(urllib.parse.parse_qsl(u.query, keep_blank_values=True))
            if route == "/library/sections" and req.get_method() == "POST":
                q["location"] = [v for k, v in urllib.parse.parse_qsl(u.query) if k == "location"][0]
        body = json.loads(req.data) if req.data else None
        return server.handle(req.get_method(), route, q, body)


FILMS = {"Name": "Films", "CollectionType": "movies", "Locations": ["/data/media/movies"]}
SERIES = {"Name": "Series", "CollectionType": "tvshows", "Locations": ["/data/media/tv"]}
MIXED = {"Name": "Odd", "CollectionType": "homevideos", "Locations": ["/data/media/home"]}
ITEMS = [{"Id": "m1", "Type": "Movie", "Name": "Dune", "ProviderIds": {"Tmdb": "438631"}, "ProductionYear": 2021, "RunTimeTicks": 90000000000},
         {"Id": "s1", "Type": "Series", "Name": "Harbour", "ProviderIds": {"Tvdb": "111"}},
         {"Id": "e1", "Type": "Episode", "Name": "Pilot", "SeriesId": "s1", "SeriesName": "Harbour", "ParentIndexNumber": 1, "IndexNumber": 1, "ProviderIds": {}}]


class Config:
    def __init__(self, services_list, active="jellyfin"):
        self.data = {"services": services_list, "extras": {"media_server": active}}
        self.lock = threading.RLock()
        self.saved = 0

    def save(self):
        self.saved += 1


class Reading(unittest.TestCase):
    def test_what_each_server_has_is_read_in_one_shape(self):
        jf = Server([FILMS, SERIES], ["Sam"])
        plex = PlexServer([{"title": "Movies", "type": "movie", "paths": ["/data/media/movies"]}, {"title": "Pics", "type": "photo", "paths": ["/p"]}])
        with mock.patch.object(services, "_fetch", World(jf=jf, plex=plex)):
            self.assertEqual(mm.read_libraries(mediaserver.Jellyfin(), [JF]), [
                {"name": "Films", "type": "movies", "folders": ["/data/media/movies"]}, {"name": "Series", "type": "tvshows", "folders": ["/data/media/tv"]}])
            self.assertEqual([(x["name"], x["type"]) for x in mm.read_libraries(mediaserver.ADAPTERS["plex"](), [PLEX])], [("Movies", "movies"), ("Pics", "photos")])

    def test_the_plan_for_libraries_and_people_keeps_what_is_there_and_says_what_it_skips(self):
        wanted = [{"name": "Films", "type": "movies", "folders": ["/a"]}, {"name": "Series", "type": "tvshows", "folders": ["/data/media/tv"]},
                  {"name": "Pics", "type": "homevideos", "folders": ["/p"]}, {"name": "Music", "type": "music", "folders": ["/m"]}, {"name": "Empty", "type": "movies", "folders": []}]
        have = [{"name": "films", "type": "movies", "folders": ["/z"]}, {"name": "TV", "type": "tvshows", "folders": ["/data/media/tv/"]}]
        got = {x["name"]: x for x in mm.plan_libraries(wanted, have, "emby")}
        self.assertEqual([got[n]["action"] for n in ("Films", "Series", "Pics", "Music", "Empty")], ["exists", "exists", "add", "add", "skip"])
        plex = {x["name"]: x for x in mm.plan_libraries(wanted, [], "plex")}
        self.assertEqual(plex["Pics"]["action"], "skip")
        self.assertIn("home videos", plex["Pics"]["why"])
        self.assertEqual([x["action"] for x in mm.plan_users(["Sam", "alex"], ["ALEX"], "jellyfin")], ["add", "exists"])
        self.assertEqual({x["action"] for x in mm.plan_users(["Sam"], [], "plex")}, {"cannot"})

    def test_own_media_offers_the_folders_that_are_there_and_have_something_in_them(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(f"{d}/movies"), os.makedirs(f"{d}/tv"), open(f"{d}/movies/a.mkv", "w").close()
            got = mm.own_libraries("x", "/data/media", host=d)
        self.assertEqual(got, [{"name": "Films", "type": "movies", "folders": ["/data/media/movies"]}])
        self.assertEqual(len(mm.own_libraries("x", "/data/media", host="")), 3)  # no media folder known: the three, to be checked


class Preview(unittest.TestCase):
    def data(self, *svc, active="jellyfin"):
        return {"services": list(svc), "extras": {"media_server": active}}

    def test_a_migration_is_read_from_both_and_changes_nothing(self):
        jf = Server([FILMS, SERIES], ["Sam", "Alex"], ITEMS)
        emby = Server([dict(FILMS, Name="Movies")], ["Sam"], prefix="/emby")
        world = World(jf=jf, emby=emby)
        with mock.patch.object(services, "_fetch", world):
            got = mm.preview(self.data(JF, EMBY), "jellyfin", "emby", "migrate", None)
        self.assertEqual(got["problem"], "")
        self.assertEqual({x["name"]: x["action"] for x in got["libraries"]}, {"Films": "exists", "Series": "add"})
        self.assertEqual({x["name"]: x["action"] for x in got["users"]}, {"Sam": "exists", "Alex": "add"})
        self.assertIn("Emby", got["history"]["says"])
        for s in (jf, emby):
            self.assertEqual({c[0] for c in s.calls}, {"GET"}, "a plan asks, never changes")

    def test_a_server_that_does_not_answer_is_a_sentence_not_an_error(self):
        with mock.patch.object(services, "_fetch", side_effect=services.ServiceError("Cannot reach Emby")):
            got = mm.preview(self.data(JF, EMBY), "jellyfin", "emby", "migrate", None)
        self.assertEqual(got["problem"], "Cannot reach Emby")
        self.assertIn("not set up", mm.preview(self.data(JF), "jellyfin", "emby", "migrate", None)["problem"])
        self.assertEqual(mm.preview(self.data(JF, EMBY), "jellyfin", "emby", "fresh", None)["libraries"], [])


class Run(unittest.TestCase):
    def run_it(self, cfg, source, target, mode, parts, world, added=("jellyfin", "emby", "plex"), data_dir=None, switch=True):
        state = {}
        with mock.patch.object(services, "_fetch", world), mock.patch.object(migrate, "_fetch", world):
            mm.run(cfg, data_dir, source, target, mode, list(parts), list(added), state, switch=switch)
        return state

    def test_jellyfin_to_emby_adds_libraries_and_people_then_watched_then_switches(self):
        with tempfile.TemporaryDirectory() as d:
            jf = Server([FILMS, SERIES, MIXED], ["Sam", "Alex"], ITEMS)
            jf.state[("u-sam", "m1")] = {"Played": True, "PlaybackPositionTicks": 0, "PlayCount": 1, "LastPlayedDate": "2026-01-02T03:04:05Z"}
            jf.state[("u-sam", "e1")] = {"Played": False, "PlaybackPositionTicks": 5000 * 10000}
            em_items = [dict(i, Id="x" + i["Id"]) for i in ITEMS]
            for i in em_items:
                if i.get("SeriesId"):
                    i["SeriesId"] = "x" + i["SeriesId"]
            emby = Server([], [], em_items, prefix="/emby")
            cfg = Config([JF, EMBY])
            state = self.run_it(cfg, "jellyfin", "emby", "migrate", ["libraries", "users", "history"], World(jf=jf, emby=emby), data_dir=d)
            self.assertEqual(state["state"], "done", state)
            self.assertEqual([x["Name"] for x in emby.libs], ["Films", "Series", "Odd"])  # home videos are a kind Emby has too
            self.assertEqual({u["Name"] for u in emby.users}, {"Sam", "Alex"})
            # each new person has a long password nobody has seen
            self.assertTrue(all(len(p) >= 24 for p in emby.passwords.values()) and len(emby.passwords) == 2)
            hist = [s for s in state["steps"] if s["part"] == "history"][0]
            self.assertIn("Marked 1 as watched and set 1 resume points in Emby", hist["said"])
            sam = emby.users[0]["Id"]
            self.assertTrue(emby.state[(sam, "xm1")]["Played"])
            self.assertEqual(emby.state[(sam, "xe1")]["PlaybackPositionTicks"], 5000 * 10000)
            self.assertEqual([s["part"] for s in state["steps"]], ["libraries", "users", "history", "switch"])
            self.assertEqual(cfg.data["extras"]["media_server"], "emby")
            self.assertEqual(cfg.data["extras"]["media_server_back"]["id"], "jellyfin")
            self.assertTrue(all(c[0] != "DELETE" for s in (jf, emby) for c in s.calls))

    def test_running_it_twice_makes_nothing_twice(self):
        with tempfile.TemporaryDirectory() as d:
            jf = Server([FILMS, SERIES], ["Sam"], ITEMS)
            jf.state[("u-sam", "m1")] = {"Played": True, "PlaybackPositionTicks": 0}
            emby = Server([], [], [dict(i, Id="x" + i["Id"], **({"SeriesId": "x" + i["SeriesId"]} if i.get("SeriesId") else {})) for i in ITEMS], prefix="/emby")
            world = World(jf=jf, emby=emby)
            self.run_it(Config([JF, EMBY]), "jellyfin", "emby", "migrate", ["libraries", "users", "history"], world, data_dir=d, switch=False)
            before = (len(emby.libs), len(emby.users))
            state = self.run_it(Config([JF, EMBY]), "jellyfin", "emby", "migrate", ["libraries", "users", "history"], world, data_dir=d, switch=False)
            self.assertEqual((len(emby.libs), len(emby.users)), before)
            self.assertEqual({i["state"] for s in state["steps"] if s["part"] in ("libraries", "users") for i in s["items"]}, {"kept"})
            self.assertIn("Marked 0 as watched", [s for s in state["steps"] if s["part"] == "history"][0]["said"])

    def test_plex_to_jellyfin_reads_the_owner_and_hands_the_rest_to_the_import_with_keep_applying(self):
        with tempfile.TemporaryDirectory() as d:
            plex = PlexServer([{"title": "Movies", "type": "movie", "paths": ["/data/media/movies"]}, {"title": "Shows", "type": "show", "paths": ["/data/media/tv"]}], ["Sam"])
            jf = Server([], ["Sam"], ITEMS)
            cfg = Config([JF, PLEX], active="plex")
            state = self.run_it(cfg, "plex", "jellyfin", "migrate", ["libraries", "history", "keep"], World(jf=jf, plex=plex), data_dir=d)
            self.assertEqual(state["state"], "done", state)
            self.assertEqual({x["Name"]: x["CollectionType"] for x in jf.libs}, {"Movies": "movies", "Shows": "tvshows"})
            self.assertTrue(jf.state[("u-sam", "m1")]["Played"])
            self.assertTrue(jf.state[("u-sam", "e1")]["Played"])
            self.assertTrue(cfg.data["extras"]["import_keep"])
            self.assertEqual(cfg.data["extras"]["media_server"], "jellyfin")

    def test_to_plex_adds_libraries_but_cannot_make_people_and_marks_the_owner_only(self):
        with tempfile.TemporaryDirectory() as d:
            jf = Server([FILMS, SERIES], ["Sam", "Alex"], ITEMS)
            jf.state[("u-sam", "m1")] = {"Played": True, "PlaybackPositionTicks": 0, "LastPlayedDate": "2026-01-02T03:04:05Z"}
            jf.state[("u-alex", "m1")] = {"Played": True, "PlaybackPositionTicks": 0}
            plex = PlexServer([], ["Sam"], seen=False)
            state = self.run_it(Config([JF, PLEX]), "jellyfin", "plex", "migrate", ["libraries", "users", "history"], World(jf=jf, plex=plex), data_dir=d)
            self.assertEqual(state["state"], "done", state)
            self.assertEqual({x["title"]: (x["type"], x["agent"]) for x in plex.libs}, {"Films": ("movie", "tv.plex.agents.movie"), "Series": ("show", "tv.plex.agents.series")})
            users = [s for s in state["steps"] if s["part"] == "users"][0]
            self.assertEqual(users["state"], "skipped")
            self.assertIn("plex.tv", users["said"])
            self.assertEqual(plex.watched, ["10"])  # Dune, for Sam only; the episode was not watched by Sam
            self.assertIn("Only Sam's history can go into Plex", [s for s in state["steps"] if s["part"] == "history"][0]["said"])

    def test_a_library_that_cannot_be_added_stops_the_switch_and_nothing_is_removed(self):
        with tempfile.TemporaryDirectory() as d:
            bad = {"Name": "Odd", "CollectionType": "movies", "Locations": ["/elsewhere/odd"]}
            jf = Server([FILMS, bad], ["Sam"], ITEMS)
            emby = Server([], [], [], prefix="/emby")
            cfg = Config([JF, EMBY])
            state = self.run_it(cfg, "jellyfin", "emby", "migrate", ["libraries"], World(jf=Server([bad], ["Sam"], ITEMS), emby=emby), data_dir=d)
            self.assertEqual(state["state"], "failed")
            self.assertIn("Nothing was switched", state["said"])
            self.assertEqual(cfg.data["extras"]["media_server"], "jellyfin")
            self.assertNotIn("media_server_back", cfg.data["extras"])

    def test_a_part_that_fails_does_not_stop_the_next_and_says_why(self):
        with tempfile.TemporaryDirectory() as d:
            jf = Server([FILMS, dict(SERIES, Locations=["/elsewhere/tv"])], ["Sam"], ITEMS)
            emby = Server([], [], [], prefix="/emby")
            cfg = Config([JF, EMBY])
            state = self.run_it(cfg, "jellyfin", "emby", "migrate", ["libraries", "users"], World(jf=jf, emby=emby), data_dir=d, switch=False)
            libs = state["steps"][0]
            self.assertEqual(libs["state"], "partly")
            self.assertIn("1 could not be added", libs["said"])
            self.assertEqual([i["state"] for i in libs["items"]], ["done", "failed"])
            self.assertIn("/elsewhere/tv", libs["items"][1]["why"])
            self.assertEqual([x["Name"] for x in emby.users], ["Sam"])  # the people were still made
            self.assertEqual(state["state"], "done")  # some failed, none failed whole: the person decides from what the steps said

    def test_start_fresh_adds_nothing_and_only_switches(self):
        jf, emby = Server([FILMS], ["Sam"]), Server([], [], prefix="/emby")
        cfg = Config([JF, EMBY])
        state = self.run_it(cfg, "jellyfin", "emby", "fresh", ["libraries", "users", "history"], World(jf=jf, emby=emby))
        self.assertEqual([s["part"] for s in state["steps"]], ["switch"])
        self.assertEqual((emby.libs, emby.users, jf.calls), ([], [], []))  # the old server is not even asked
        self.assertEqual(cfg.data["extras"]["media_server"], "emby")

    def test_import_your_own_media_adds_the_folders_to_the_new_server_only(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(mm, "_host_media", return_value=None), mock.patch.object(mm, "_inside", return_value="/data/media"):
            jf, emby = Server([FILMS], ["Sam"]), Server([], [], prefix="/emby")
            cfg = Config([JF, EMBY])
            state = self.run_it(cfg, "jellyfin", "emby", "own", ["libraries", "users", "history"], World(jf=jf, emby=emby), data_dir=d)
        self.assertEqual([x["Name"] for x in emby.libs], ["Films", "Series", "Music"])
        self.assertEqual(emby.users, [])
        self.assertEqual({c[0] for c in jf.calls}, set(), "the old server is not asked at all")
        self.assertEqual(state["state"], "done")

    def test_the_same_server_is_refused_and_a_bad_way_too(self):
        with self.assertRaises(ValueError):
            mm.run(Config([JF]), None, "jellyfin", "jellyfin", "migrate", [], ["jellyfin"], {})
        with self.assertRaises(ValueError):
            mm.run(Config([JF]), None, "jellyfin", "emby", "teleport", [], ["jellyfin"], {})

    def test_an_unreadable_old_server_stops_before_anything_is_changed(self):
        with tempfile.TemporaryDirectory() as d:
            emby = Server([], [], prefix="/emby")
            cfg = Config([JF, EMBY])

            class Down(World):
                def __call__(self, service, req, timeout):
                    if "jf" in req.full_url:
                        raise services.ServiceError("Cannot reach Jellyfin")
                    return super().__call__(service, req, timeout)
            state = self.run_it(cfg, "jellyfin", "emby", "migrate", ["libraries", "users"], Down(emby=emby), data_dir=d)
        self.assertEqual(state["state"], "failed")
        self.assertEqual((emby.libs, emby.users), ([], []))
        self.assertEqual(cfg.data["extras"]["media_server"], "jellyfin")


class Installed(unittest.TestCase):
    """DASH-586: a Plex or Emby in Manage apps (from Install apps or by hand) is installed and not in use, ready to choose."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name

    def state(self, pid):
        return next((p for p in pa.basics(self.d) if p["id"] == pid), None)

    def test_each_is_added_when_its_app_is_there_and_active_once_it_has_its_key(self):
        self.assertEqual(pa.ensure_installed(self.d, [JF]), [])  # Jellyfin is added by its own default
        self.assertIsNone(self.state("plex"))
        self.assertEqual(pa.ensure_installed(self.d, [dict(PLEX, api_key=""), EMBY]), ["plex", "emby"])
        self.assertEqual((self.state("plex")["state"], self.state("emby")["state"]), ("installed", "enabled"))
        self.assertEqual(pa.ensure_installed(self.d, [dict(PLEX, api_key=""), EMBY]), [])  # nothing again
        self.assertEqual(pa.ensure_installed(self.d, [PLEX, EMBY]), ["plex"])  # the key arrived: now it can be chosen
        self.assertEqual(self.state("plex")["state"], "enabled")

    def test_a_state_a_person_chose_is_never_changed_and_a_removed_one_is_not_added_again(self):
        pa.ensure_installed(self.d, [PLEX])
        pa.set_state(self.d, "plex", "disabled")
        self.assertEqual(pa.ensure_installed(self.d, [PLEX]), [])
        self.assertEqual(self.state("plex")["state"], "disabled")
        os.makedirs(os.path.join(self.d, "plugins", ".removed", "emby-20261127"))
        self.assertEqual(pa.ensure_installed(self.d, [EMBY]), [])
        self.assertIsNone(self.state("emby"))

    def test_a_switched_off_app_does_not_count_and_the_record_runs_nothing(self):
        self.assertEqual(pa.ensure_installed(self.d, [dict(PLEX, enabled=False)]), [])
        pa.ensure_installed(self.d, [PLEX])
        self.assertFalse(os.path.exists(os.path.join(self.d, "plugins", "plex", "compose.yaml")))


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = server.make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        r, _ = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": "correct horse battery"}, cookie=False)
        cls.cookie = r.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def call(cls, method, path, body=None, cookie=True):
        c = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        h = {"Content-Type": "application/json", "X-Starboard": "1"}
        if cookie:
            h["Cookie"] = cls.cookie
        c.request(method, path, json.dumps(body) if body is not None else None, h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        return r, json.loads(raw) if raw[:1] in (b"{", b"[") else raw

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_it_needs_a_sign_in_and_refuses_what_is_not_asked_for(self):
        self.assertEqual(self.call("GET", "/api/media-server/migrate", cookie=False)[0].status, 401)
        self.assertEqual(self.call("POST", "/api/media-server/migrate", {"id": "emby", "mode": "own"}, cookie=False)[0].status, 401)
        self.assertEqual(self.call("GET", "/api/media-server/migrate")[1], {"state": "none"})
        self.assertEqual(self.call("POST", "/api/media-server/migrate", {"id": "kodi", "mode": "own"})[0].status, 400)
        self.assertEqual(self.call("POST", "/api/media-server/migrate", {"id": "emby", "mode": "teleport"})[0].status, 400)
        r, got = self.call("POST", "/api/media-server/migrate", {"id": "emby", "mode": "own"})
        self.assertEqual(r.status, 409)  # Emby is not added as a plug-in here
        self.assertIn("not added", got["error"] if isinstance(got, dict) and "error" in got else str(got))

    def test_the_move_runs_in_the_background_and_the_page_reads_how_it_went(self):
        import time as _time
        jf = Server([FILMS], ["Sam"], ITEMS)
        emby = Server([], [], prefix="/emby")
        self.app.config.data["services"] = [dict(JF), dict(EMBY)]
        with mock.patch.object(server.Handler, "media_servers_added", return_value=["jellyfin", "emby"]), \
                mock.patch.object(services, "_fetch", World(jf=jf, emby=emby)), mock.patch.object(migrate, "_fetch", World(jf=jf, emby=emby)):
            r, got = self.call("POST", "/api/media-server/migrate", {"id": "emby", "mode": "migrate", "parts": ["libraries", "users"]})
            self.assertEqual(r.status, 200, got)
            for _ in range(100):
                state = self.call("GET", "/api/media-server/migrate")[1]
                if state["state"] != "running":
                    break
                _time.sleep(0.05)
        self.assertEqual(state["state"], "done", state)
        self.assertEqual([s["part"] for s in state["steps"]], ["libraries", "users", "switch"])
        self.assertEqual(self.app.config.data["extras"]["media_server"], "emby")
        self.assertEqual([x["Name"] for x in emby.libs], ["Films"])


if __name__ == "__main__":
    unittest.main()
