const express = require("express");

const app = express();
app.use(express.json());

app.get("/healthz", (_req, res) => {
  res.json({ status: "ok" });
});

app.post("/render", (req, res) => {
  res.status(202).json({
    status: "accepted",
    template: req.body?.template ?? "default",
    message: "Render pipeline placeholder is ready for Remotion integration.",
  });
});

const port = Number(process.env.PORT || 3100);
app.listen(port, "0.0.0.0", () => {
  console.log(`remotion renderer listening on ${port}`);
});
