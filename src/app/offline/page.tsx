import Link from 'next/link';
import { WifiOff } from 'lucide-react';
export default function Offline() {
  return (
    <main className="app-main" id="main">
      <div className="app-panel offline-panel">
        <WifiOff className="mx-auto" size={35} />
        <h1>You’re offline. / आप ऑफ़लाइन हैं।</h1>
        <p>
          Your saved draft stays on this device. Reconnect to continue your search.
          <br />
          आपका ड्राफ्ट इस डिवाइस पर सुरक्षित है। आगे बढ़ने के लिए इंटरनेट से जुड़ें।
        </p>
        <Link className="button dark" href="/">
          Try again / फिर कोशिश करें
        </Link>
      </div>
    </main>
  );
}
