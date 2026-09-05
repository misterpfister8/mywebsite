async (page) => {
  const origin = await page.evaluate(() => location.origin);
  await page.goto(origin + "/sechserrechner/");
  if ((await page.locator("html").getAttribute("data-theme")) === "light")
    await page.locator("[data-theme-toggle]").click();
  await page.setViewportSize({ width: 390, height: 844 });
  const results = [];
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const check = (ok, label) => {
    if (!ok) throw Error(label);
    results.push(label);
  };
  const text = async (id) => await page.locator(id).textContent();
  await page.getByRole("textbox", { name: "Note 1", exact: true }).fill("4,5");
  await page.getByRole("textbox", { name: "Note 2", exact: true }).fill("6");
  await page
    .getByRole("textbox", { name: "Gewicht der Note 2", exact: true })
    .fill("2");
  check(
    (await text("#average")) === "5.50",
    "Weighted mean + decimal comma = 5.50",
  );
  await page.locator("#targetAverage").fill("6");
  check(
    (await text("#planningResult")).includes("Nicht erreichbar"),
    "Impossible target",
  );
  await page.locator("#targetAverage").fill("1");
  check(
    (await text("#planningResult")).includes("gesichert"),
    "Guaranteed target",
  );
  await page.locator("#targetAverage").fill("5.5");
  check(
    (await text("#planningResult")).includes("5.48"),
    "Planner uses rounded target",
  );
  await page.getByRole("textbox", { name: "Note 1", exact: true }).fill("6.01");
  check(
    (await text("#message")).includes("zwischen"),
    "Reject out-of-range grade",
  );
  check(
    await page.locator("#resultArea").isHidden(),
    "Invalid input hides stale result",
  );
  await page
    .getByRole("textbox", { name: "Note 1", exact: true })
    .fill("4.555");
  check(
    (await text("#message")).includes("Dezimalstellen"),
    "Reject excessive grade precision",
  );
  await page.getByRole("textbox", { name: "Note 1", exact: true }).fill("4,5");
  await page
    .getByRole("textbox", { name: "Gewicht der Note 2", exact: true })
    .fill("0");
  check((await text("#message")).includes("Gewichte"), "Reject zero weight");
  await page
    .getByRole("textbox", { name: "Gewicht der Note 2", exact: true })
    .fill("2");
  await page
    .getByRole("textbox", { name: "Note 1", exact: true })
    .press("Enter");
  check((await text("#average")) === "5.50", "Enter retains calculation");
  await page
    .getByRole("button", { name: "+ Note hinzufügen", exact: true })
    .click();
  check((await page.locator(".grade-row").count()) === 3, "Add grade");
  await page
    .getByRole("button", { name: "Notenzeile 3 entfernen", exact: true })
    .click();
  check((await page.locator(".grade-row").count()) === 2, "Remove grade");
  await page.getByRole("button", { name: "Zurücksetzen", exact: true }).click();
  check(
    (await page.locator("#resultArea").isHidden()) &&
      (await page.locator(".grade-row").count()) === 2,
    "Reset calculator",
  );
  await page.locator(".grade-input").first().fill("3.99");
  await page.locator(".grade-input").nth(1).fill("4");
  check((await text("#average")) === "4.00", "Round half hundredth correctly");
  await page
    .getByRole("link", { name: "Danach: Schlaf planen ↗", exact: true })
    .click();
  check(
    (await text("#resultTime")) === "22:50",
    "07:00 minus 8h and 10min = 22:50",
  );
  check(
    (await text("#resultLabel")).includes("Vorabend"),
    "Previous evening label",
  );
  await page.locator("#wakeTime").fill("23:00");
  await page.locator("#calculateBtn").click();
  check(
    (await text("#resultTime")) === "14:50" &&
      (await text("#resultLabel")).includes("selben Tag"),
    "Same day bedtime",
  );
  await page.locator("#sleepHours").fill("7,5");
  await page.locator("#calculateBtn").click();
  check((await text("#resultTime")) === "15:20", "Sleep decimal comma");
  await page.locator("#sleepHours").fill("7.25");
  await page.locator("#calculateBtn").click();
  check(
    (await text("#message")).includes("30 Minuten") &&
      (await page.locator("#sleepResult").isHidden()),
    "Reject invalid sleep increment",
  );
  await page.locator("#sleepHours").fill("8");
  await page.locator("#fallAsleepMinutes").fill("181");
  await page.locator("#calculateBtn").click();
  check((await text("#message")).includes("180"), "Reject excessive latency");
  await page.locator("#fallAsleepMinutes").fill("15");
  await page.locator("#wakeTime").fill("07:00");
  await page.locator("#calculateBtn").click();
  await page.clock.install({ time: new Date(2026, 8, 5, 23, 30) });
  await page
    .getByRole("radio", { name: "Ich gehe jetzt ins Bett", exact: true })
    .check();
  check(
    await page.locator("#wakeField").isHidden(),
    "Now mode hides wake time",
  );
  await page.locator("#calculateBtn").click();
  check(
    (await text("#resultTime")) === "07:45" &&
      (await text("#resultLabel")).includes("Morgen"),
    "Now mode crosses midnight",
  );
  await page.clock.resume();
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/", "/sechserrechner/", "/sleepcalculator/"]) {
      await page.goto(origin + path);
      check(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `No horizontal overflow ${width} ${path}`,
      );
    }
  }
  await page.goto(origin + "/");
  await page.emulateMedia({ reducedMotion: "reduce" });
  check(
    (await page
      .locator(".cube")
      .evaluate((el) => getComputedStyle(el).animationName)) === "none",
    "Reduced motion stops animation",
  );
  check(
    await page.locator(".motion-toggle").isHidden(),
    "Reduced motion hides unnecessary motion control",
  );
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page
    .getByRole("button", { name: "Bewegung pausieren", exact: true })
    .click();
  check(
    (await page
      .locator(".cube")
      .evaluate((el) => getComputedStyle(el).animationPlayState)) === "paused",
    "Pause motion works",
  );
  await page.locator("[data-theme-toggle]").click();
  await page.reload();
  check(
    (await page.locator("html").getAttribute("data-theme")) === "light",
    "Theme persists",
  );
  await page.getByRole("link", { name: "Werkzeuge", exact: true }).click();
  check(page.url().endsWith("#projekte"), "Anchor navigation");
  await page.locator(".project-grade a").click();
  check(page.url().includes("/sechserrechner/"), "Grade card navigation");
  await page.locator(".back-link").click();
  await page.locator(".project-sleep a").click();
  check(
    page.url().includes("/sleepcalculator/"),
    "Sleep card and back navigation",
  );
  check(errors.length === 0, "No browser JavaScript errors");
  return { passed: results.length, results, errors };
}
