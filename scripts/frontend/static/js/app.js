let accelCtx = document.getElementById('accelChart').getContext('2d');
let gyroCtx = document.getElementById('gyroChart').getContext('2d');
// reference timestamp for relative x-axis (seconds since start)
let firstTs = null;

// Use simple categorical labels (human-readable times) so Chart.js doesn't need a
// date adapter. This avoids blank charts when the adapter is not loaded.
let accelChart = new Chart(accelCtx, {
  type: 'line',
  data: { labels: [], datasets: [
    {label: 'ax', data: [], borderColor: 'red', fill:false, tension:0.1},
    {label: 'ay', data: [], borderColor: 'green', fill:false, tension:0.1},
    {label: 'az', data: [], borderColor: 'blue', fill:false, tension:0.1}
  ]},
  options: { animation: false, responsive: true, spanGaps: true, elements: { point: { radius: 2 } } }
});

let gyroChart = new Chart(gyroCtx, {
  type: 'line',
  data: { labels: [], datasets: [
    {label: 'gx', data: [], borderColor: 'orange', fill:false, tension:0.1},
    {label: 'gy', data: [], borderColor: 'purple', fill:false, tension:0.1},
    {label: 'gz', data: [], borderColor: 'brown', fill:false, tension:0.1}
  ]},
  options: { animation: false, responsive: true, spanGaps: true, elements: { point: { radius: 2 } } }
});

async function fetchData(){
  const samples = document.getElementById('samples').value || 200;
  // use latest_file_points which returns messages from newest file in chronological order
  const res = await fetch(`/api/latest_file_points?count=${samples}`);
  const arr = await res.json();

  const labels = [];
  const ax = [], ay = [], az = [];
  const gx = [], gy = [], gz = [];

  for(const item of arr){
    const t = item.ts || Date.now();
    if(firstTs === null){ firstTs = t; }
    // relative seconds since first sample
    const rel = ((t - firstTs) / 1000.0);
    labels.push(rel.toFixed(1) + 's');

    if(item.accel){
      ax.push(item.accel.x != null ? item.accel.x : Number.NaN);
      ay.push(item.accel.y != null ? item.accel.y : Number.NaN);
      az.push(item.accel.z != null ? item.accel.z : Number.NaN);
    } else {
      ax.push(Number.NaN); ay.push(Number.NaN); az.push(Number.NaN);
    }

    if(item.gyro){
      gx.push(item.gyro.x != null ? item.gyro.x : Number.NaN);
      gy.push(item.gyro.y != null ? item.gyro.y : Number.NaN);
      gz.push(item.gyro.z != null ? item.gyro.z : Number.NaN);
    } else {
      gx.push(Number.NaN); gy.push(Number.NaN); gz.push(Number.NaN);
    }
  }

  accelChart.data.labels = labels;
  accelChart.data.datasets[0].data = ax;
  accelChart.data.datasets[1].data = ay;
  accelChart.data.datasets[2].data = az;
  accelChart.update();

  gyroChart.data.labels = labels;
  gyroChart.data.datasets[0].data = gx;
  gyroChart.data.datasets[1].data = gy;
  gyroChart.data.datasets[2].data = gz;
  gyroChart.update();
  showLoadedCount(labels.length);
}

// --- Live streaming support ---
let lastMessageJSON = null;
async function pollAndAppend(){
  try{
    const samples = Math.max(50, parseInt(document.getElementById('samples').value || 200));
    const res = await fetch(`/api/latest_file_points?count=${samples}`);
    const arr = await res.json();
    if(!Array.isArray(arr) || arr.length === 0) return;

    // find index of lastMessageJSON in arr
    let startIdx = 0;
    if(lastMessageJSON){
      for(let i=0;i<arr.length;i++){
        if(JSON.stringify(arr[i]) === lastMessageJSON){
          startIdx = i+1; break;
        }
      }
    }

    // if lastMessage not found, but arr has messages newer than last known ts, try to append by ts
    if(startIdx === 0 && lastMessageJSON){
      try{
        const last = JSON.parse(lastMessageJSON);
        for(let i=0;i<arr.length;i++){
          if(arr[i].ts > last.ts){ startIdx = i; break; }
        }
      }catch(e){}
    }

    // append messages from startIdx .. end
    if(startIdx < arr.length){
      const newItems = arr.slice(startIdx);
      for(const item of newItems){
        const t = item.ts || Date.now();
        if(firstTs === null){ firstTs = t; }
        const rel = ((t - firstTs) / 1000.0);
        const label = rel.toFixed(1) + 's';
        // push label
        accelChart.data.labels.push(label);
        gyroChart.data.labels.push(label);

        // accel
        if(item.accel){
          accelChart.data.datasets[0].data.push(item.accel.x != null ? item.accel.x : Number.NaN);
          accelChart.data.datasets[1].data.push(item.accel.y != null ? item.accel.y : Number.NaN);
          accelChart.data.datasets[2].data.push(item.accel.z != null ? item.accel.z : Number.NaN);
        } else {
          accelChart.data.datasets[0].data.push(Number.NaN);
          accelChart.data.datasets[1].data.push(Number.NaN);
          accelChart.data.datasets[2].data.push(Number.NaN);
        }

        // gyro
        if(item.gyro){
          gyroChart.data.datasets[0].data.push(item.gyro.x != null ? item.gyro.x : Number.NaN);
          gyroChart.data.datasets[1].data.push(item.gyro.y != null ? item.gyro.y : Number.NaN);
          gyroChart.data.datasets[2].data.push(item.gyro.z != null ? item.gyro.z : Number.NaN);
        } else {
          gyroChart.data.datasets[0].data.push(Number.NaN);
          gyroChart.data.datasets[1].data.push(Number.NaN);
          gyroChart.data.datasets[2].data.push(Number.NaN);
        }

        // keep charts to reasonable length (trim older points)
        const maxPoints = Math.max(100, parseInt(document.getElementById('samples').value || 200));
        while(accelChart.data.labels.length > maxPoints){
          accelChart.data.labels.shift();
          accelChart.data.datasets.forEach(ds=>ds.data.shift());
          gyroChart.data.labels.shift();
          gyroChart.data.datasets.forEach(ds=>ds.data.shift());
        }
      }

      accelChart.update();
      gyroChart.update();
      const total = accelChart.data.labels.length;
      showLoadedCount(total);
      lastMessageJSON = JSON.stringify(arr[arr.length-1]);
    }
  }catch(e){
    // ignore polling errors
    console.debug('poll error', e);
  }
}

// Start streaming by polling every 1s
setInterval(pollAndAppend, 1000);

// reset timeline when user clicks manual refresh
document.getElementById('refresh').addEventListener('click', ()=>{ firstTs = null; lastMessageJSON = null; fetchData(); });


document.getElementById('refresh').addEventListener('click', fetchData);

let auto = false;
document.getElementById('autorefresh').addEventListener('change',(e)=>{auto=e.target.checked});

// Load a batch of samples once on page load (default 20)
window.addEventListener('load', () => {
  fetchData();
});

// Optional periodic refresh if user enables it
setInterval(()=>{ if(auto) fetchData() }, 3000);

// show number of points loaded for quick debugging
function showLoadedCount(n){
  // create a small status element if not exists
  let s = document.getElementById('loadedCount');
  if(!s){
    s = document.createElement('div');
    s.id = 'loadedCount';
    s.style.marginLeft = '12px';
    document.querySelector('.controls').appendChild(s);
  }
  s.textContent = `Loaded ${n} points`;
}
