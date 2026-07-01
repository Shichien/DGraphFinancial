import { nextTick } from "vue";

export async function flashMetric(id) {
  await nextTick();
  const element = document.getElementById(id);
  const metric = element?.closest(".metric");
  if (!metric) return;
  metric.classList.remove("flash");
  void metric.offsetWidth;
  metric.classList.add("flash");
}
