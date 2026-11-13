import { QRCodeSVG } from 'qrcode.react';

/** Mã QR để quét bằng camera điện thoại. Luôn nền trắng chữ đen, kể cả giao diện tối (QR nền tối nhiều máy quét không đọc được). */
export function QrCode({ value, size = 160, label }: { value: string; size?: number; label: string }) {
  return (
    <div className="fx-qr" style={{ width: size + 24, height: size + 24 }}>
      <QRCodeSVG value={value} size={size} level="M" bgColor="#ffffff" fgColor="#111111" marginSize={0} role="img" aria-label={label} />
    </div>
  );
}
