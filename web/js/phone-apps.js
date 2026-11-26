// Phone apps for Calibre-Web (DASH-583, owner, 26 November 2026): the three Starboard offers where Calibre-Web is set up,
// on the Calibre-Web plug-in's page and in Manage apps beside the app. Plain links; nothing is loaded or asked until
// the page that shows them is opened.
const PHONE_APPS = [
  { os: "Android", name: "KOReader", why: "an e-reader that opens your Calibre-Web library over OPDS: add the address of Calibre-Web followed by /opds",
    links: [["KOReader's download page", "https://koreader.rocks/"], ["KOReader on F-Droid", "https://f-droid.org/packages/org.koreader.launcher.fdroid/"]] },
  { os: "Android", name: "Calibre-Web-Companion", why: "an app made for Calibre-Web: sign in to your Calibre-Web with its address, read books in the app and keep your place",
    links: [["Calibre-Web-Companion on F-Droid", "https://f-droid.org/en/packages/de.doen1el.calibreWebCompanion/"], ["Calibre-Web-Companion on Google Play", "https://play.google.com/store/apps/details?id=de.doen1el.calibreWebCompanion"]] },
  { os: "iPhone and iPad", name: "Readest", why: "a free reader that connects to Calibre-Web and to OPDS catalogues",
    links: [["Readest on the App Store", "https://apps.apple.com/app/id6738622779"], ["Readest's own page", "https://readest.com/"]] },
];

function phoneApps(heading = "h3") {
  const out = el("div", { class: "stack-2", "data-phone-apps": "" },
    el("p", { class: "small muted", text: "Starboard does not run these and has not tested them with your library. Use the address Starboard shows for Calibre-Web, from your home network. Each app is made by others." }));
  for (const os of [...new Set(PHONE_APPS.map((a) => a.os))]) {
    out.append(el(heading, { text: os }), el("ul", { class: "plain-list" }, PHONE_APPS.filter((a) => a.os === os).map((a) => el("li", {},
      el("strong", { text: a.name }), `: ${a.why}. `,
      ...a.links.flatMap(([text, href], i) => [i ? " · " : "", el("a", { href, target: "_blank", rel: "noopener noreferrer" }, text, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))])))));
  }
  return out;
}
