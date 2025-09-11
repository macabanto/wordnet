// server.js
import express from 'express';
import cors from 'cors';
import { MongoClient, ObjectId } from 'mongodb';
const app = express();
const PORT = process.env.PORT || 3001;
const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017'; // use 127.0.0.1 to avoid odd IPv6 issues
const DB_NAME = process.env.DB_NAME || 'lemmas';
const COLLECTION = process.env.COLLECTION || 'lemmas-linked-second-degree';

app.use(cors({
  origin: ['https://macabanto.github.io', 'http://localhost:5173'], // add dev + prod origins
  methods: ['GET', 'OPTIONS'], // allow preflight
  allowedHeaders: ['Content-Type'], // safe default
  maxAge: 86400 // cache preflight for 24h
}));
// Fail fast if Mongo isn't reachable
const client = new MongoClient(MONGO_URI, { serverSelectionTimeoutMS: 3000 });
let collection;

async function start() {
  try {
    console.log('Connecting to Mongo at:', MONGO_URI);
    await client.connect();
    await client.db('admin').command({ ping: 1 });
    console.log('✅ Mongo connected');

    const db = client.db(DB_NAME);
    collection = db.collection(COLLECTION);
//  what i previously had
    /* 
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`✅ Server listening on http://0.0.0.0:${PORT}`);
    });
    */
    app.listen(process.env.PORT || 3001, '0.0.0.0', () => {
      console.log('API listening on 0.0.0.0:' + (process.env.PORT || 3001));
    });
  } catch (err) {
    console.error('❌ Mongo connection failed:', err?.message || err);
    process.exit(1);
  }
}
//testing

app.get("/", (req, res) => {
  res.send("✅ Tunnel is working!");
});

app.get('/ping', (req, res) => res.send('pong'));

app.get('/api/term/:id', async (req, res) => {
  const { id } = req.params;

  if (!ObjectId.isValid(id)) {
    return res.status(400).json({ error: 'Invalid ID format' });
  }

  try {
    console.log('🔎 findOne _id:', id);
    const doc = await collection.findOne({ _id: new ObjectId(id) });

    if (!doc) {
      console.log('⚠️  Not found:', id);
      return res.status(404).json({ error: 'Term not found' });
    }

    res.json(doc);
  } catch (err) {
    console.error('❌ Query error:', err?.message || err);
    res.status(500).json({ error: 'Server error' });
  }
});

process.on('SIGINT', async () => {
  await client.close().catch(() => {});
  process.exit(0);
});

start();