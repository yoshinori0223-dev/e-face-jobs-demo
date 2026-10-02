const $=x=>document.getElementById(x),
EFACE_JOBS=JOBS.map(x=>({...x,source:x.source||"eface"})),
HW_LIVE=(typeof HELLOWORK_LIVE_TEST_JOBS!=="undefined"?HELLOWORK_LIVE_TEST_JOBS:[]),
HW_DEMO=(typeof HELLOWORK_JOBS!=="undefined"?HELLOWORK_JOBS:[]),
ALL_JOBS=[...EFACE_JOBS,...HW_LIVE,...HW_DEMO],
icons={"コールセンター":"🎧","オフィスワーク":"💻","軽作業・物流":"📦","販売・接客":"🏪","製造・工場":"🏭","医療・介護":"⚕","事務・経理":"¥","営業・セールス":"💼"};
let chosen="";

const cats=[...new Set(ALL_JOBS.map(x=>x.cat))];
cats.forEach(c=>{let o=document.createElement("option");o.value=c;o.textContent=c;$("cat").appendChild(o)});
$("cats").innerHTML=cats.map(c=>`<button class="cat" data-c="${c}"><i>${icons[c]||"●"}</i><b>${c}</b><small>${ALL_JOBS.filter(x=>x.cat===c).length}件</small></button>`).join("");

function matches(j){
 let q=$("q").value.toLowerCase(),p=$("place").value.toLowerCase(),c=$("cat").value||chosen,t=$("type").value;
 return (!q||[j.title,j.company,j.area,j.cat,...(j.tags||[])].join(" ").toLowerCase().includes(q))
   &&(!p||j.area.toLowerCase().includes(p))
   &&(!c||j.cat===c)
   &&(!t||j.type===t);
}
function cardHtml(j,i,isHw=false){
 const badge=["人気","新着","正社員"][i]||"おすすめ";
 const img=isHw
   ? `<div class="pic hw-pic"><span>${icons[j.cat]||"👤"}</span></div>`
   : `<div class="pic">${j.image?`<img src="${j.image}" alt="${j.cat}のイメージ画像" loading="lazy">`:(icons[j.cat]||"👤")}<span class="recommend-label label-${i}">${badge}</span></div>`;
 return `<article class="card ${isHw?"hw-card":"recommend-card"}" data-id="${j.id}">${img}<div class="body">${isHw?'<span class="source-badge hw-live">ハローワーク公開求人・テスト表示</span>':""}<h3>${j.title}</h3><div class="meta">${j.company}</div><div class="meta">📍 ${j.area}</div><div class="pay">${j.pay}</div><div class="tags">${(j.tags||[]).map(x=>`<span>${x}</span>`).join("")}</div></div></article>`;
}
function render(){
 const eface=EFACE_JOBS.filter(matches);
 const hw=HW_LIVE.filter(matches);
 $("count").textContent=`検索結果 ${eface.length+hw.length}件`;
 $("cards").innerHTML=eface.slice(0,3).map((j,i)=>cardHtml(j,i,false)).join("")||"<p>該当するおすすめ求人がありません。</p>";
 $("hwCards").innerHTML=hw.map((j,i)=>cardHtml(j,i,true)).join("")||"<p>該当するハローワーク求人がありません。</p>";
 document.querySelectorAll(".card").forEach(e=>e.onclick=()=>show(e.dataset.id));
}
function show(id){location.href="job-detail.html?id="+encodeURIComponent(id)}
$("go").onclick=()=>{chosen="";render();$("jobs").scrollIntoView()};
["cat","type"].forEach(x=>$(x).onchange=()=>{chosen="";render()});
document.querySelectorAll("[data-k]").forEach(e=>e.onclick=()=>{let k=e.dataset.k;if(k==="福岡市")$("place").value=k;else $("q").value=k;chosen="";render();$("jobs").scrollIntoView()});
document.querySelectorAll("[data-c]").forEach(e=>e.onclick=()=>{chosen=e.dataset.c;$("cat").value=chosen;render();$("jobs").scrollIntoView()});
function reset(){$("q").value="";$("place").value="";$("cat").value="";$("type").value="";chosen="";render()}
$("reset").onclick=$("all").onclick=reset;
$("close").onclick=()=>$("modal").classList.add("hide");
$("modal").onclick=e=>{if(e.target===$("modal"))$("modal").classList.add("hide")};
render();