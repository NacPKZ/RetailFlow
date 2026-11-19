// Pont de lancement pour l'aperçu web et npm run dev, sans dépendance Node.
import { spawn } from 'node:child_process';
const args=process.argv.slice(2);
const value=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const port=value('--port','8501'),host=value('--host','127.0.0.1');
if(!/^\d+$/.test(port))throw new Error('Port invalide');
const child=spawn('python',['-m','streamlit','run','app.py','--server.address',host,
  '--server.port',port,'--browser.gatherUsageStats','false'],{stdio:'inherit',shell:false});
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,()=>child.kill(signal));
child.on('exit',code=>process.exit(code??0));
