// Full Backend Code (Node.js)
const express = require('express');
const mongoose = require('mongoose');
const http = require('http');
const { Server } = require('socket.io');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = require("socket.io")(server,{cors: {origin:"*"}});

// Middleware
app.use(express.json());
app.set('view engine', 'ejs');
app.use(express.static('public'));



const multer = require('multer');
const path = require('path');
app.use(express.static('uploads'));
// Configure multer storage with custom filename and extension
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, 'uploads/'); // Define the upload directory
  },
  filename: function (req, file, cb) {
    // Get the file extension (e.g., .mp4, .jpg, etc.)
    const ext = path.extname(file.originalname);
    // Use original file name but with a new random prefix and the correct extension
    cb(null, Date.now() + ext); // New file name: timestamp.extension
  }
});

// Set up multer with the custom storage configuration
const upload = multer({ storage: storage });



// MongoDB Connection
const MONGO_URI = "mongodb+srv://avin:avin@cluster0.fhxczjk.mongodb.net/aigleair?retryWrites=true&w=majority";

mongoose.connect(MONGO_URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true
}).then(() => console.log('MongoDB Connected'))
  .catch(err => console.error(err));

// System Schema and Model
const deviceSchema = new mongoose.Schema({
  macAddress: String,
  name: String,
  location: String,
  isOnline: Boolean,
  data: {
    temperature: Number,
    humidity: Number,
    pHLevel: Number,
    solarVolt : Number,
    co2_ppm : Number,
    tuebidity : Number,
    ldr_state : String,
  },
  lastUpdated: Date,
});



const System = mongoose.model('System', deviceSchema);
const advertisementSchema = new mongoose.Schema({
  companyName: { type: String, required: true },
  description: { type: String, required: true },
  content: { type: String, required: true }, // Path to the uploaded file
  macAddresses: { type: [String], required: true }, // Array of device MAC addresses
  createdAt: { type: Date, default: Date.now },
  status: { type: String, enum: ['pending', 'approved', 'rejected'], default: 'pending' }
});

const Advertisement = mongoose.model('Advertisement', advertisementSchema);
// API Routes
app.get('/api/systems', async (req, res) => {
    const systems = await System.find();
    res.json(systems);
});
app.get('/company', async (req, res) => {
  const systems = await System.find();
  res.render("company" , {systems});
});
app.post('/company', upload.single('adFile'), async (req, res) => {
  const { companyName, description, devices } = req.body;
  const adFile = req.file;

  const adRequests = devices.map(device => ({
      content: adFile.path, // Store file path or move it to a permanent location
      macAddresses : device,
      companyName,
      description,
  }));
  console.log(adRequests)
  await Advertisement.insertMany(adRequests);

  res.status(201).json({ message: 'Ad requests submitted successfully' });
});

app.get('/api/systems/:macAddress', async (req, res) => {
    const { macAddress } = req.params;
    const system = await System.findOne({ macAddress });
    console.log(system)
    res.render('home', {system })
    // if (!system) return res.status(404).send('System not found');
    // res.json(system);
});
app.get('/api/system/:macaddress', async (req, res) => {
  const macAddress = req.params.macaddress;
  try {
      const system = await System.findOne({ macAddress }); // Replace with your MongoDB query
      res.json(system);
  } catch (error) {
      console.error(error);
      res.status(500).json({ error: 'Error fetching system data' });
  }
});
// Route to fetch all ad requests
app.get('/ads/requests', async (req, res) => {
  try {
      const ads = await Advertisement.find();
      res.render('approveAds', { ads });
  } catch (error) {
      console.error(error);
      res.status(500).json({ error: 'Error fetching ad requests' });
  }
});
// Route to display ads for a specific device
app.get('/ads/device/:macAddress', async (req, res) => {
  try {
      const { macAddress } = req.params;
      const ads = await Advertisement.find({
          macAddresses: macAddress,
          status: 'approved',
      });
      res.render('displayAds', { ads });
  } catch (error) {
      console.error(error);
      res.status(500).json({ error: 'Error fetching ads' });
  }
});

// Route to approve an ad
app.post('/ads/approve/:id', async (req, res) => {
  try {
      const { id } = req.params;
      await Advertisement.findByIdAndUpdate(id, { status: 'approved' });
      res.redirect('/ads/requests'); // Redirect back to the approve ads page
  } catch (error) {
      console.error(error);
      res.status(500).json({ error: 'Error approving ad' });
  }
});


app.post('/api/systems/:macAddress', async (req, res) => {
    const { macAddress } = req.params;
    const updates = req.body;
    const system = await System.findOneAndUpdate({ macAddress }, updates, { new: true });
    if (!system) return res.status(404).send('System not found');
    io.emit('update', { macAddress, updates });
    res.status(200).json(system);
});

// WebSocket
io.on('connection', (socket) => {
    console.log('A user connected');
    socket.on('disconnect', () => console.log('User disconnected'));
});

// EJS Route
app.get('/', async (req, res) => {
    const systems = await System.find();
    res.render('index', { systems });
});

// Start Server
const PORT = process.env.PORT || 80;
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));


