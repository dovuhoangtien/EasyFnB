import { Route, Routes } from 'react-router';
import { Shell } from './components/Shell';
import { ToastProvider } from './components/ui';
import Assistant from './pages/Assistant';
import Camera from './pages/Camera';
import LiveAssistant from './pages/live/LiveAssistant';
import LiveDashboard from './pages/live/LiveDashboard';
import LiveSetup from './pages/live/LiveSetup';
import LiveStaffPhone from './pages/live/LiveStaffPhone';
import PhoneCamera from './pages/live/PhoneCamera';
import Overview from './pages/Overview';
import Regulars from './pages/Regulars';
import Report from './pages/Report';
import Staff from './pages/Staff';
import StaffChannels from './pages/StaffChannels';
import StaffPhone from './pages/StaffPhone';

function Dashboard() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/camera" element={<Camera />} />
        <Route path="/nhan-vien" element={<Staff />} />
        <Route path="/app-nhan-vien" element={<StaffChannels />} />
        <Route path="/khach-quen" element={<Regulars />} />
        <Route path="/tro-ly" element={<Assistant />} />
        <Route path="/bao-cao" element={<Report />} />
        {/* Chạy thật: dữ liệu từ máy chủ và camera */}
        <Route path="/truc-tiep" element={<LiveDashboard />} />
        <Route path="/truc-tiep/cai-dat" element={<LiveSetup />} />
        <Route path="/truc-tiep/tro-ly" element={<LiveAssistant />} />
        <Route path="*" element={<Overview />} />
      </Routes>
    </Shell>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        {/* App trên điện thoại nhân viên: không có khung quản lý */}
        <Route path="/nv" element={<StaffPhone />} />
        <Route path="/nv/:id" element={<StaffPhone />} />
        <Route path="/phat" element={<PhoneCamera />} />
        <Route path="/nv-tt" element={<LiveStaffPhone />} />
        <Route path="/nv-tt/:id" element={<LiveStaffPhone />} />
        <Route path="/*" element={<Dashboard />} />
      </Routes>
    </ToastProvider>
  );
}
