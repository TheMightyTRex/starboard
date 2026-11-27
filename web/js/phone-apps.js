// Phone apps for Calibre-Web and Kavita (DASH-583, owner, 26 November 2026): the apps Starboard offers where each is set up,
// on its plug-in's page and in Manage apps beside the app. Plain links; nothing is loaded or asked until
// the page that shows them is opened.
const PHONE_APPS_CALIBRE = [
  { os: "Android", name: "KOReader", why: "an e-reader that opens your Calibre-Web library over OPDS: add the address of Calibre-Web followed by /opds",
    links: [["KOReader's download page", "https://koreader.rocks/"], ["KOReader on F-Droid", "https://f-droid.org/packages/org.koreader.launcher.fdroid/"]] },
  { os: "Android", name: "Calibre-Web-Companion", why: "an app made for Calibre-Web: sign in to your Calibre-Web with its address, read books in the app and keep your place",
    links: [["Calibre-Web-Companion on F-Droid", "https://f-droid.org/en/packages/de.doen1el.calibreWebCompanion/"], ["Calibre-Web-Companion on Google Play", "https://play.google.com/store/apps/details?id=de.doen1el.calibreWebCompanion"]] },
  { os: "iPhone and iPad", name: "Readest", why: "a free reader that connects to Calibre-Web and to OPDS catalogues",
    links: [["Readest on the App Store", "https://apps.apple.com/app/id6738622779"], ["Readest's own page", "https://readest.com/"]] },
];

// Kavita's own words: each person finds the address and the Auth key under their user settings, on the 3rd Party Clients tab.
const PHONE_APPS_KAVITA = [
  { os: "Android", name: "KOReader", why: "an e-reader that opens your library over OPDS: add an OPDS catalogue and paste the address from the 3rd Party Clients tab",
    links: [["KOReader's download page", "https://koreader.rocks/"], ["KOReader on F-Droid", "https://f-droid.org/packages/org.koreader.launcher.fdroid/"], ["Kavita's KOReader guide", "https://wiki.kavitareader.com/guides/3rdparty/koreader/"]] },
  { os: "Android", name: "Kover", why: "an unofficial app made for Kavita: sign in with your address and Auth key. Tested with Kavita on 26 November 2026. It is also in open beta for iPhone and iPad on TestFlight",
    links: [["Kover on Google Play", "https://play.google.com/store/apps/details?id=com.rodonisi.kover"], ["Kover's project page", "https://github.com/rodonisi/kover"], ["Kover's releases (APK)", "https://github.com/rodonisi/kover/releases"], ["Kover on TestFlight", "https://testflight.apple.com/join/UsCtQUeY"]] },
  { os: "iPhone and iPad", name: "Sutra", why: "a free reader that uses OPDS and keeps your page in step with Kavita. It needs iOS 17",
    links: [["Sutra on the App Store", "https://apps.apple.com/app/id6780096864"]] },
  { os: "iPhone and iPad", name: "Komic", why: "a reader for comics and manga. It needs your Auth key, and away from home it needs an https address",
    links: [["Komic on the App Store", "https://apps.apple.com/dk/app/id6744676973"]] },
];
const PHONE_SETS = {
  "calibre-web": { apps: PHONE_APPS_CALIBRE, need: "Use the address Starboard shows for Calibre-Web, from your home network." },
  kavita: { apps: PHONE_APPS_KAVITA, need: "Each needs your Kavita address and your Auth key, which Kavita shows under your user settings, on the 3rd Party Clients tab. Use the address Starboard shows for Kavita, from your home network." },
};

function phoneApps(heading = "h3", which = "calibre-web") {
  const set = PHONE_SETS[which];
  const out = el("div", { class: "stack-2", "data-phone-apps": "" },
    el("p", { class: "small muted", text: `Starboard does not run these and has not tested them with your library. ${set.need} Each app is made by others.` }));
  if (which === "kavita") {
    out.append(el("p", { class: "small" }, el("a", { href: "https://wiki.kavitareader.com/guides/3rdparty/kavita-dedicated", target: "_blank", rel: "noopener noreferrer" },
      "More apps made for Kavita", el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))));
  }
  for (const os of [...new Set(set.apps.map((a) => a.os))]) {
    out.append(el(heading, { text: os }), el("ul", { class: "plain-list" }, set.apps.filter((a) => a.os === os).map((a) => el("li", {},
      el("strong", { text: a.name }), `: ${a.why}. `,
      ...a.links.flatMap(([text, href], i) => [i ? " · " : "", el("a", { href, target: "_blank", rel: "noopener noreferrer" }, text, el("span", { class: "visually-hidden", text: " (opens in a new tab)" }))])))));
  }
  return out;
}
