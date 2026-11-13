import { Navigate, Route, Routes, useParams } from 'react-router';
import OwnerShell from './app/OwnerShell';
import Now from './app/Now';
import Assistant from './app/Assistant';
import Shift from './app/Shift';
import Settings from './app/Settings';
import StaffPhone from './app/StaffPhone';
import PhoneCamera from './pages/live/PhoneCamera';

/** Link cũ /nv-tt/:id (đã gửi cho nhân viên) vẫn mở được */
function OldStaffLink() {
  const { id } = useParams();
  return <Navigate to={id ? `/nv/${id}` : '/nv'} replace />;
}

export default function App() {
  return (
    <Routes>
      {/* Chủ quán */}
      <Route element={<OwnerShell />}>
        <Route index element={<Now />} />
        <Route path="tro-ly" element={<Assistant />} />
        <Route path="ca" element={<Shift />} />
        <Route path="cai-dat" element={<Settings />} />
      </Route>

      {/* Nhân viên, mở trên điện thoại */}
      <Route path="nv" element={<StaffPhone />} />
      <Route path="nv/:id" element={<StaffPhone />} />
      {/* Điện thoại làm camera */}
      <Route path="phat" element={<PhoneCamera />} />

      {/* Đường dẫn cũ */}
      <Route path="nv-tt" element={<OldStaffLink />} />
      <Route path="nv-tt/:id" element={<OldStaffLink />} />
      <Route path="truc-tiep" element={<Navigate to="/" replace />} />
      <Route path="truc-tiep/cai-dat" element={<Navigate to="/cai-dat" replace />} />
      <Route path="truc-tiep/tro-ly" element={<Navigate to="/tro-ly" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
