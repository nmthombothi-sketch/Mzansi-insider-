/* Mzansi Insider — bursary save & deadline reminder
   Works on a deployed static site using localStorage (per-device) and an
   .ics calendar download for the deadline. No backend required.
   A future Mzansi Insider account will sync saves and send email alerts. */
(function () {
  "use strict";

  var STORE_KEY = "mzansi_saved_bursaries";

  function readSaved() {
    try {
      return JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
    } catch (e) {
      return {};
    }
  }

  function writeSaved(obj) {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(obj));
      return true;
    } catch (e) {
      return false;
    }
  }

  function note(el, msg) {
    if (el) el.textContent = msg;
  }

  function pad(n) { return (n < 10 ? "0" : "") + n; }

  function buildICS(name, deadlineISO) {
    // All-day reminder on the deadline date.
    var d = deadlineISO.replace(/-/g, "");
    var stamp = new Date();
    var dt =
      stamp.getUTCFullYear() +
      pad(stamp.getUTCMonth() + 1) +
      pad(stamp.getUTCDate()) +
      "T" +
      pad(stamp.getUTCHours()) +
      pad(stamp.getUTCMinutes()) +
      pad(stamp.getUTCSeconds()) +
      "Z";
    return [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Mzansi Insider//Bursary Reminder//EN",
      "BEGIN:VEVENT",
      "UID:" + d + "-" + Math.random().toString(36).slice(2) + "@mzansiinsider",
      "DTSTAMP:" + dt,
      "DTSTART;VALUE=DATE:" + d,
      "SUMMARY:" + name + " — bursary closes",
      "DESCRIPTION:Application deadline for the " + name + ". Confirm the exact date on the official site.",
      "BEGIN:VALARM",
      "TRIGGER:-P3D",
      "ACTION:DISPLAY",
      "DESCRIPTION:" + name + " bursary closes in 3 days",
      "END:VALARM",
      "END:VEVENT",
      "END:VCALENDAR"
    ].join("\r\n");
  }

  function download(filename, text) {
    var blob = new Blob([text], { type: "text/calendar;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var box = document.querySelector(".bursary-actions");
    if (!box) return;

    var id = box.getAttribute("data-bursary");
    var name = box.getAttribute("data-name") || "Bursary";
    var iso = box.getAttribute("data-deadline");
    var label = box.getAttribute("data-deadline-label") || "";

    var saveBtn = document.getElementById("save-btn");
    var remindBtn = document.getElementById("remind-btn");
    var noteEl = document.getElementById("save-note");

    // Reflect saved state on load
    var saved = readSaved();
    if (saved[id] && saveBtn) {
      saveBtn.classList.add("saved");
      saveBtn.textContent = "✓ Saved";
    }

    if (saveBtn) {
      saveBtn.addEventListener("click", function () {
        var store = readSaved();
        if (store[id]) {
          delete store[id];
          writeSaved(store);
          saveBtn.classList.remove("saved");
          saveBtn.textContent = "♥ Save bursary";
          note(noteEl, "Removed from your saved bursaries on this device.");
        } else {
          store[id] = { name: name, deadline: iso, label: label, saved: Date.now() };
          writeSaved(store);
          saveBtn.classList.add("saved");
          saveBtn.textContent = "✓ Saved";
          note(noteEl, "Saved on this device. A free Mzansi Insider account (coming soon) will sync saves and email you deadline alerts.");
        }
      });
    }

    if (remindBtn) {
      remindBtn.addEventListener("click", function () {
        if (!iso) {
          note(noteEl, "Deadline date will be confirmed closer to the application window.");
          return;
        }
        try {
          download(id + "-deadline.ics", buildICS(name, iso));
          note(noteEl, "Calendar reminder downloaded — it will alert you 3 days before " + label + ". Always confirm the date on the official site.");
        } catch (e) {
          note(noteEl, "Couldn't create the calendar file on this device. Note the deadline: " + label + ".");
        }
      });
    }
  });
})();
