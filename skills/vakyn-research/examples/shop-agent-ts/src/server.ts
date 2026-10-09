import express from "express";
import { chatTurn } from "./agent.js";
import { writeDescription } from "./catalog.js";
import { moderateReview } from "./moderation.js";

const app = express();
app.use(express.json());

// About 8,000 chat turns a day on the shop site.
app.post("/chat", async (req, res) => {
  res.json({ reply: await chatTurn(req.body.history) });
});

// About 1,200 reviews a day.
app.post("/reviews", async (req, res) => {
  const approved = await moderateReview(req.body.text);
  res.json({ status: approved ? "published" : "held" });
});

// A few dozen new products a week.
app.post("/admin/products/describe", async (req, res) => {
  res.json({ description: await writeDescription(req.body) });
});

app.listen(3000);
