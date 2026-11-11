import { useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router';
import { Merge, ShieldCheck, Split } from 'lucide-react';
import { Empty, useToast } from '../components/ui';
import type { Person } from '../sim/model';
import { useSim } from '../sim/store';
import { clock } from '../sim/util';

function initials(p: Person) {
  if (!p.name) return `#${p.id.slice(1)}`;
  const words = p.name.trim().split(/\s+/);
  return words[words.length - 1].charAt(0).toUpperCase();
}

function NameForm({ person, onSave }: { person: Person; onSave: (name: string) => void }) {
  const [value, setValue] = useState(person.name ?? '');
  const submit = (ev: FormEvent) => {
    ev.preventDefault();
    onSave(value);
  };
  return (
    <form className="flex gap-2 w-full" onSubmit={submit}>
      <label className="visually-hidden" htmlFor="person-name">
        Tên khách
      </label>
      <input id="person-name" className="input" value={value} placeholder="Đặt tên, ví dụ Anh Tuấn" onChange={(ev) => setValue(ev.target.value)} />
      <button type="submit" className="btn btn--primary" disabled={value.trim() === (person.name ?? '')}>
        Lưu tên
      </button>
    </form>
  );
}

export default function Regulars() {
  const e = useSim();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const filter = params.get('loc') ?? 'all';
  const selected = e.person(params.get('nguoi') ?? '') ?? e.people[0];
  const shown = e.people.filter((p) => (filter === 'named' ? !!p.name : filter === 'unnamed' ? !p.name : true));
  const today = e.visits.filter((v) => v.person === selected.id);
  const set = (next: Record<string, string>) => setParams({ ...Object.fromEntries(params), ...next }, { replace: true });

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Khách quen</h1>
          <p>Khuôn mặt được tự gom theo từng người. Đặt tên một lần, lần sau khách tới nhân viên sẽ được báo.</p>
        </div>
        <div className="seg" role="group" aria-label="Lọc danh sách">
          {[
            ['all', 'Tất cả'],
            ['named', 'Đã đặt tên'],
            ['unnamed', 'Chưa đặt tên'],
          ].map(([key, label]) => (
            <button key={key} type="button" aria-pressed={filter === key} onClick={() => set({ loc: key })}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="split">
        <section className="panel" aria-label="Nhóm khuôn mặt">
          {shown.length === 0 ? (
            <Empty title="Không còn ai chưa đặt tên">
              <p>Mọi nhóm khuôn mặt đều đã có tên. Nhóm mới sẽ xuất hiện ở đây sau vài lần khách ghé.</p>
            </Empty>
          ) : (
            <div className="faces">
              {shown.map((p) => (
                <button key={p.id} type="button" className="face" aria-pressed={p.id === selected.id} onClick={() => set({ nguoi: p.id })}>
                  <span className="avatar" aria-hidden="true">
                    {initials(p)}
                  </span>
                  <span className="face-name" data-unnamed={!p.name}>
                    {p.name ?? 'Thêm tên'}
                  </span>
                  <span className="tiny muted">{p.visits} lần ghé</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="panel" aria-labelledby="person-title">
          <div className="detail-section flex flex-col items-center gap-3 text-center">
            <span className="avatar avatar--lg" aria-hidden="true">
              {initials(selected)}
            </span>
            <h2 id="person-title" className="text-center">
              {e.personName(selected.id)}
            </h2>
            {selected.consent === 'yes' ? (
              <span className="chip chip--ok">
                <ShieldCheck size={13} aria-hidden="true" />
                Đã đồng ý nhận diện
              </span>
            ) : (
              <span className="chip">Chờ khách đồng ý, tự xoá sau {selected.expiresInDays} ngày</span>
            )}
            <NameForm
              key={selected.id}
              person={selected}
              onSave={(name) => {
                e.rename(selected.id, name);
                toast(name.trim() ? `Đã lưu tên "${name.trim()}". Lần sau khách tới, nhân viên sẽ nghe tên này.` : 'Đã bỏ tên của nhóm này.');
              }}
            />
          </div>
          <div className="detail-section">
            <dl className="kv">
              <dt>Số lần ghé</dt>
              <dd>{selected.visits}</dd>
              <dt>Ảnh khuôn mặt đã gom</dt>
              <dd>{selected.faces}</dd>
              <dt>Hôm nay</dt>
              <dd>{today.length ? `vào lúc ${clock(today[today.length - 1].arrived, false)}` : 'chưa ghé'}</dd>
            </dl>
          </div>
          <div className="detail-section">
            <label className="small muted" htmlFor="person-note">
              Ghi chú cho nhân viên
            </label>
            <textarea
              id="person-note"
              key={`note-${selected.id}`}
              className="input mt-2"
              defaultValue={selected.note ?? ''}
              placeholder="Ví dụ: dị ứng tôm, thích ngồi gần cửa sổ"
              onBlur={(ev) => e.setNote(selected.id, ev.target.value)}
            />
          </div>
          <div className="detail-section">
            <h3 className="small muted mb-2">Các lần ghé gần đây</h3>
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Ngày</th>
                  <th scope="col" className="num">
                    Giờ
                  </th>
                  <th scope="col" className="num">
                    Bàn
                  </th>
                  <th scope="col" className="num">
                    Số người
                  </th>
                </tr>
              </thead>
              <tbody>
                {[...today]
                  .reverse()
                  .map((v) => ({ date: 'Hôm nay', time: clock(v.arrived, false), table: v.table, party: v.party }))
                  .concat(selected.past)
                  .slice(0, 5)
                  .map((v) => (
                    <tr key={`${v.date}-${v.time}`}>
                      <td>{v.date}</td>
                      <td className="num">{v.time}</td>
                      <td className="num">{v.table}</td>
                      <td className="num">{v.party}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          <div className="detail-section flex gap-2 flex-wrap">
            <button type="button" className="btn" onClick={() => toast('Chọn một nhóm khác để gộp. Ảnh của hai nhóm sẽ thành một người.')}>
              <Merge size={16} aria-hidden="true" />
              Gộp với người khác
            </button>
            <button type="button" className="btn" onClick={() => toast('Chọn những ảnh không phải người này để tách ra nhóm mới.')}>
              <Split size={16} aria-hidden="true" />
              Không phải người này
            </button>
          </div>
        </section>
      </div>

      <section className="panel" aria-labelledby="privacy-title">
        <div className="panel-head">
          <h2 id="privacy-title">Quyền riêng tư</h2>
        </div>
        <div className="panel-body small ink2">
          <p>
            Khuôn mặt là dữ liệu nhạy cảm theo Luật Bảo vệ dữ liệu cá nhân. Easy FnB chỉ nhận diện khách đã đồng ý, lưu dữ liệu khuôn mặt ngay trên máy tại quán và
            tự xoá nhóm chưa được đồng ý sau 30 ngày. Nhân viên được nhận diện bằng đồng phục, số áo và khuôn mặt đăng ký lúc vào ca, có sự đồng ý của họ.
          </p>
        </div>
      </section>
    </div>
  );
}
