import { initializeApp, getApp, getApps } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const env = import.meta.env;

const firebaseConfig = {
  apiKey: env.VITE_AUTH_API_KEY || env.VITE_FIREBASE_API_KEY,
  authDomain: env.VITE_AUTH_DOMAIN || env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: env.VITE_AUTH_PROJECT_ID || env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: env.VITE_AUTH_STORAGE_BUCKET || env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: env.VITE_AUTH_MESSAGING_SENDER_ID || env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: env.VITE_AUTH_APP_ID || env.VITE_FIREBASE_APP_ID,
};

const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

googleProvider.setCustomParameters({ prompt: "select_account" });

export { app, auth, googleProvider };
