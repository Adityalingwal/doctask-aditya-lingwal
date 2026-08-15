// One date shape for the whole screen: day, short month — "15 Aug" — never
// the locale-dependent month-first order `toLocaleString` alone would give
// in some browsers. Built by hand from the parts so the order never drifts.
const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export function dayMonth(iso) {
  const moment = new Date(iso);
  if (Number.isNaN(moment.getTime())) {
    return iso;
  }
  return `${moment.getDate()} ${MONTHS[moment.getMonth()]}`;
}

export function dayMonthTime(iso) {
  const moment = new Date(iso);
  if (Number.isNaN(moment.getTime())) {
    return iso;
  }
  const hours = String(moment.getHours()).padStart(2, "0");
  const minutes = String(moment.getMinutes()).padStart(2, "0");
  return `${dayMonth(iso)}, ${hours}:${minutes}`;
}
