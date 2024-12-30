const express = require("express");
const mongoose = require("mongoose");
const http = require("http");
const socketIo = require("socket.io");
const cors = require("cors");

// MongoDB connection
const MONGO_URI = "mongodb+srv://avin:avin@cluster0.fhxczjk.mongodb.net/aigleair?retryWrites=true&w=majority";
mongoose.connect(MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true });
const db = mongoose.connection;

db.on("error", console.error.bind(console, "MongoDB connection error:"));
db.once("open", () => {
  console.log("MongoDB connected!");
});

// Define the Device schema
const deviceSchema = new mongoose.Schema({
  macAddress: String,
  name: String,
  location: String,
  isOnline: Boolean,
  data: {
    temperature: Number,
    humidity: Number,
    pHLevel: Number,
  },
  lastUpdated: Date,
});

const Device = mongoose.model("Device", deviceSchema);

// Express and Socket.IO setup
const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// Middleware
app.use(cors());
app.use(express.static("public"));
app.set("view engine", "ejs");

// Routes
app.get("/", async (req, res) => {
  const devices = await Device.find();
  res.render("home", { devices });
});

// Real-time data fetch
io.on("connection", (socket) => {
  console.log("Client connected");

  const interval = setInterval(async () => {
    const devices = await Device.find();
    socket.emit("updateDevices", devices);
  }, 3000);

  socket.on("disconnect", () => {
    clearInterval(interval);
    console.log("Client disconnected");
  });
});

// Start server
const PORT = 5000;
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
