import { useState } from 'react';
import { Outlet, useLocation } from 'react-router';
import { CircleHelp, Copy, ExternalLink, LayoutGrid, MessageCircle as MessagesCircle, MessagesSquare, Moon, Sun, QrCode as QrIcon, ReceiptText, ScanEye, Settings as SettingsIcon, Shield, ShieldCheck, Smartphone } from 'lucide-react';
import { AppShell } from '@astryxdesign/core/AppShell';
import { Avatar } from '@astryxdesign/core/Avatar';
import { Button } from '@astryxdesign/core/Button';
import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { IconButton } from '@astryxdesign/core/IconButton';
import { Text } from '@astryxdesign/core/Text';
import { useToast } from '@astryxdesign/core/Toast';
import { useTheme } from '@astryxdesign/core/theme';
import { useThemeChoice } from './themeMode';
import { SideNav, SideNavHeading, SideNavItem } from '@astryxdesign/core/SideNav';
import { putSettings } from '../live/api';
import { useRun } from '../live/hooks';
import { live, useLive, useLiveConnection } from '../live/store';
import { ROLE_LABEL } from '../live/text';
import { RouteFade } from './motion';
import { QrCode } from './QrCode';
import { Tour, useTour } from './tour';
import { Conn, usePhoneBase } from './ui';

const TABS = [
  { href: '/', label: 'Quán lúc này', icon: LayoutGrid },
  { href: '/tro-ly', label: 'Trợ lý', icon: MessagesSquare },
  { href: '/nhom', label: 'Nhắn nhóm', icon: MessagesCircle },
  { href: '/ca', label: 'Ca hôm nay', icon: ReceiptText },
];

/** Link app điện thoại của từng nhân viên: chép hoặc mở thử */
function StaffLinks({ onClose }: { onClose: () => void }) {
  const staff = useLive((s) => s.staff);
  const base = usePhoneBase();
  const toast = useToast();
  const [qr, setQr] = useState<string | null>(null);
  const copy = (url: string, name: string) => {
    navigator.clipboard
      .writeText(url)
      .then(() => toast({ body: `Đã chép link của ${name}` }))
      .catch(() => toast({ body: 'Không chép được, hãy chép tay đường link.', type: 'error', isAutoHide: true }));
  };
  return (
    <>
      <DialogHeader title="App nhân viên" subtitle="Mỗi người quét mã QR (hoặc mở link) của mình trên điện thoại. Chạy ở quán thì dùng cùng Wi-Fi với máy chủ." onOpenChange={onClose} />
      <div className="flex flex-col gap-1 p-4">
        {staff.length === 0 && (
          <EmptyState
            isCompact
            title="Chưa có nhân viên"
            description="Thêm nhân viên trong Cài đặt để có link cho từng người."
            actions={<Button label="Mở Cài đặt" href="/cai-dat?tab=nhan-vien" variant="primary" onClick={onClose} />}
          />
        )}
        {staff.map((s) => {
          const url = `${base}/nv/${encodeURIComponent(s.id)}`;
          const showQr = qr === s.id;
          return (
            <div key={s.id} className="flex flex-col">
              <div className="flex items-center gap-3 py-2">
                <Avatar name={s.name} size="md" tooltip={false} />
                <div className="min-w-0 flex-1">
                  <Text type="label" weight="semibold" as="p">
                    {s.name}
                  </Text>
                  <Text type="supporting" color="secondary" as="p" maxLines={1}>
                    {ROLE_LABEL[s.role]}
                    {s.online ? ', đang mở app' : ''}
                  </Text>
                </div>
                <IconButton
                  label={showQr ? `Ẩn mã QR của ${s.name}` : `Hiện mã QR của ${s.name}`}
                  tooltip="Mã QR"
                  variant={showQr ? 'secondary' : 'ghost'}
                  icon={<QrIcon size={16} />}
                  onClick={() => setQr(showQr ? null : s.id)}
                />
                <IconButton label={`Chép link của ${s.name}`} tooltip="Chép link" variant="ghost" icon={<Copy size={16} />} onClick={() => copy(url, s.name)} />
                <IconButton label={`Mở app của ${s.name}`} tooltip="Mở thử" variant="ghost" icon={<ExternalLink size={16} />} href={url} target="_blank" />
              </div>
              {showQr && (
                <div className="flex flex-col items-center gap-2 pb-3">
                  <QrCode value={url} size={180} label={`Mã QR mở app của ${s.name}`} />
                  <Text type="supporting" color="secondary" as="p" className="text-center">
                    {s.name} quét bằng camera điện thoại, mở link, rồi bấm “Bắt đầu ca”.
                  </Text>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}

/** Nút "Trông quán": bật tay là coi như quán đóng; ngoài giờ mở cửa thì máy chủ tự trông */
function GuardButton() {
  const settings = useLive((s) => s.settings);
  const { busy, run } = useRun();
  if (!settings) return null;
  const manual = settings.guard_mode === true;
  const byHours = settings.closed === true && !manual;
  const on = manual || byHours;
  const toggle = async () => {
    const out = await run('guard', () => putSettings({ guard_mode: !manual }), manual ? 'Đã tắt trông quán' : 'Đang trông quán');
    if (out) live.setSettings(out);
  };
  const note = byHours
    ? `Ngoài giờ, tự trông tới ${settings.open_time ?? 'giờ mở cửa'}`
    : manual
      ? 'Đang trông: có người vào sẽ báo chủ quán'
      : settings.close_time
        ? `Tự bật lúc ${settings.close_time}`
        : null;
  return (
    <div className="fx-guard" data-on={on || undefined}>
      <Button
        label={on ? 'Đang trông quán' : 'Trông quán'}
        variant={on ? 'primary' : 'secondary'}
        size="sm"
        icon={on ? <ShieldCheck size={15} /> : <Shield size={15} />}
        aria-pressed={on}
        isDisabled={byHours}
        tooltip={byHours ? 'Quán đang ngoài giờ mở cửa nên tự trông' : undefined}
        isLoading={busy === 'guard'}
        onClick={() => void toggle()}
      />
      {note && <span className="fx-guard-note">{note}</span>}
    </div>
  );
}

/** Khung của chủ quán: thanh bên với ba mục và Cài đặt; trên điện thoại thanh bên thành ngăn kéo */
export default function OwnerShell() {
  useLiveConnection();
  const { pathname } = useLocation();
  const [links, setLinks] = useState(false);
  const status = useLive((s) => s.status);
  const dark = useTheme().mode === 'dark';
  const { setChoice } = useThemeChoice();
  const tour = useTour();

  return (
    <AppShell
      contentPadding={5}
      sideNav={
        <SideNav
          aria-label="Điều hướng chính"
          collapsible
          header={
            <SideNavHeading
              icon={
                <span className="fx-mark">
                  <ScanEye size={17} strokeWidth={2.4} aria-hidden="true" />
                </span>
              }
              heading="Easy FnB"
              headingHref="/"
            />
          }
          footer={
            <div className="fx-side-foot">
              <Conn status={status} />
              <GuardButton />
              <span data-tour="staff-app" className="flex flex-col">
                <Button label="App nhân viên" variant="secondary" size="sm" icon={<Smartphone size={15} />} onClick={() => setLinks(true)} />
              </span>
              <Button label="Hướng dẫn" variant="ghost" size="sm" icon={<CircleHelp size={15} />} onClick={tour.start} />
              <Button label={dark ? 'Giao diện sáng' : 'Giao diện tối'} variant="ghost" size="sm" icon={dark ? <Sun size={15} /> : <Moon size={15} />} onClick={() => setChoice(dark ? 'light' : 'dark')} />
            </div>
          }
        >
          {TABS.map((t) => (
            <SideNavItem key={t.href} href={t.href} label={t.label} icon={<t.icon size={16} aria-hidden="true" />} isSelected={pathname === t.href} />
          ))}
          <SideNavItem href="/cai-dat" label="Cài đặt" icon={<SettingsIcon size={16} aria-hidden="true" />} isSelected={pathname === '/cai-dat'} />
        </SideNav>
      }
    >
      <RouteFade id={pathname}>
        <Outlet />
      </RouteFade>
      <Dialog isOpen={links} onOpenChange={setLinks} width={440} padding={0}>
        <StaffLinks onClose={() => setLinks(false)} />
      </Dialog>
      {tour.open && <Tour onClose={tour.stop} />}
    </AppShell>
  );
}
