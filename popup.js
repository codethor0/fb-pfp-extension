/* fb-pfp popup: image storage, cycle state, and run orchestration.
 *
 * Everything stays on the local machine. Images the user picked are kept in
 * chrome.storage.local as ArrayBuffers, never sent anywhere: the only network
 * destination involved in a run is facebook.com itself, by the tab the
 * extension drives.
 */

const $ = (id) => document.getElementById(id);
const status = (msg) => { $("status").textContent = msg; };

const storageGet = (keys) => new Promise((resolve) => chrome.storage.local.get(keys, resolve));
const storageSet = (obj) => new Promise((resolve) => chrome.storage.local.set(obj, resolve));

async function refreshStoredHint() {
  const { images = [], used = [] } = await storageGet(["images", "used"]);
  $("stored").textContent = images.length
    ? `${images.length} image(s) stored, ${used.length} used this round.`
    : "No images stored yet.";
}

$("files").addEventListener("change", async (event) => {
  const picked = [...event.target.files];
  if (picked.length === 0) return;
  const images = [];
  for (const file of picked) {
    images.push({
      name: file.name,
      type: file.type || "image/jpeg",
      data: await file.arrayBuffer(),
    });
  }
  await storageSet({ images, used: [] });
  status(`${images.length} image(s) stored locally.`);
  refreshStoredHint();
});

async function run(dryRun) {
  const { images = [], used = [] } = await storageGet(["images", "used"]);
  if (images.length === 0) {
    status("Pick images first.");
    return;
  }

  // Cycle: prefer images not yet used this round; reset when all are used.
  const fresh = images.filter((img) => !used.includes(img.name));
  const pool = fresh.length > 0 ? fresh : images;
  const chosen = pool[Math.floor(Math.random() * pool.length)];

  status("Opening your Facebook profile...");
  const tab = await new Promise((resolve) =>
    chrome.tabs.create({ url: "https://www.facebook.com/me", active: true }, resolve)
  );

  // Wait for the profile page to finish loading, then inject the driver.
  await new Promise((resolve) => {
    const onUpdated = (tabId, info) => {
      if (tabId === tab.id && info.status === "complete") {
        chrome.tabs.onUpdated.removeListener(onUpdated);
        resolve();
      }
    };
    chrome.tabs.onUpdated.addListener(onUpdated);
  });

  await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });

  const reply = await chrome.tabs.sendMessage(tab.id, {
    type: "fb-pfp:run",
    image: chosen,
    dryRun,
  });

  if (reply.ok) {
    const newUsed = [...used.filter((n) => n !== chosen.name), chosen.name];
    await storageSet({ used: newUsed.length >= images.length ? [] : newUsed });
    status(dryRun ? "Dry run OK: image reached the dialog, nothing saved." : "Profile picture changed.");
  } else {
    status(`Failed: ${reply.error}`);
  }
  refreshStoredHint();
}

$("dry").addEventListener("click", () => run(true).catch((e) => status(`Error: ${e.message}`)));
$("go").addEventListener("click", () => run(false).catch((e) => status(`Error: ${e.message}`)));

refreshStoredHint();
