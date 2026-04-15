res.setHeader("Content-Type", "application/pdf");
    res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
    res.status(200).send(fileBuffer);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to generate PDF";
    res.status(400).json({ error: message });
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
    if (outputPath) {
      await fs.rm(path.dirname(outputPath), { recursive: true, force: true }).catch(() => {});
    }
  }
});