import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

console.log("index.jsx loaded");
console.log("Root element:", document.getElementById('root'));

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element not found!');
}

console.log("Creating React root");
const root = ReactDOM.createRoot(rootElement);

console.log("Rendering App");
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

console.log("App rendered successfully");

