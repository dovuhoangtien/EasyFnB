import { useState } from 'react';
import { Outlet, useLocation } from 'react-router';
import { Copy, ExternalLink, LayoutGrid, MessagesSquare, ReceiptText, ScanEye, Settings as SettingsIcon, Smartphone } from 'lucide-react';
import { AppShell } from '@astryxdesign/core/AppShell';
import { Avatar } from '@astryxdesign/core/Avatar';
import { Button } from '@astryxdesign/core/Button';
import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { IconButton } from '@astryxdesign/core/IconButton';
import { Text } from '@astryxdesign/core/Text';
import { useToast } from '@astryxdesign/core/Toast';
import { TopNav, TopNavHeading, TopNavItem } from '@astryxdesign/core/TopNav';
import { useLive, useLiveConnection } from '../live/store';
import { ROLE_LABEL } from '../live/text';
import { RouteFade } from './motion';
import { Conn, usePhoneBase } from './ui';

const TABS = [
  { href: '/', label: 'Quán lúc này', icon: LayoutGrid },
  { href: '/tro-ly', label: 'Trợ lý', icon: MessagesSquare },
  { href: '/ca', label: 'Ca hôm nay', icon: ReceiptText },
];

/** Link app điện thoại của từng nhân viên: chép hoặc mở thử */
function StaffLinks({ onClose }: { onClose: () => void }) {
  const staff = useLive((s) => s.staff);
  const base = usePhoneBase();
  const toast = useToast();
  const copy = (url: string, name: string) => {
    navigator.clipboard
      .writeText(url)
      .then(() => toast({ body: `Đã chép link của ${name}` }))
      .catch(() => toast({ body: 'Không chép được, hãy chép tay đường link.', type: 'error', isAutoHide: true }));
  };
  return (
    <>
      <DialogHeader title="App nhân viên" subtitle="Mỗi người mở link của mình trên điện thoại, cùng Wi-Fi với máy chủ." onOpenChange={onClose} />
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
          return (
            <div key={s.id} className="flex items-center gap-3 py-2">
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
              <IconButton label={`Chép link của ${s.name}`} tooltip="Chép link" variant="ghost" icon={<Copy size={16} />} onClick={() => copy(url, s.name)} />
              <IconButton label={`Mở app của ${s.name}`} tooltip="Mở thử" variant="ghost" icon={<ExternalLink size={16} />} href={url} target="_blank" />
            </div>
          );
        })}
      </div>
    </>
  );
}

/** Khung của chủ quán: thanh trên cùng với ba mục, không có thanh bên */
export default function OwnerShell() {
  useLiveConnection();
  const { pathname } = useLocation();
  const [links, setLinks] = useState(false);
  const status = useLive((s) => s.status);

  return (
    <AppShell
      contentPadding={5}
      topNav={
        <TopNav
          label="Điều hướng chính"
          heading={<TopNavHeading logo={
                <span className="fx-mark">
                  <ScanEye size={17} strokeWidth={2.4} aria-hidden="true" />
                </span>
              } logoLabel="Easy FnB" heading="Easy FnB" headingHref="/" />}
          endContent={
            <div className="flex items-center gap-2">
              <Conn status={status} />
              <Button label="App nhân viên" variant="secondary" size="sm" icon={<Smartphone size={15} />} onClick={() => setLinks(true)} />
              <IconButton label="Cài đặt" tooltip="Cài đặt" variant={pathname === '/cai-dat' ? 'secondary' : 'ghost'} icon={<SettingsIcon size={18} />} href="/cai-dat" />
            </div>
          }
        >
          {TABS.map((t) => (
            <TopNavItem key={t.href} href={t.href} label={t.label} icon={<t.icon size={16} aria-hidden="true" />} isSelected={pathname === t.href} />
          ))}
        </TopNav>
      }
    >
      <RouteFade id={pathname}>
        <Outlet />
      </RouteFade>
      <Dialog isOpen={links} onOpenChange={setLinks} width={440} padding={0}>
        <StaffLinks onClose={() => setLinks(false)} />
      </Dialog>
    </AppShell>
  );
}
