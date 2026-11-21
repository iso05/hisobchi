import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import CalculatorPage from './components/CalculatorPage.jsx';
import Admin from './Admin.jsx';
import './styles.css';

const path = window.location.pathname;
const servicePages = ['/ai-yordamchi', '/ariza', '/ai-ariza', '/ai-xizmat'];
const Page = path === '/admin' ? Admin : servicePages.includes(path) ? App : CalculatorPage;

createRoot(document.getElementById('root')).render(<React.StrictMode><Page /></React.StrictMode>);
