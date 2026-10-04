"use strict";
const $ = id => document.getElementById(id);
let bootstrap, activeRequestId = "REQ-CUSTOM", currentResult = null, analyzedRequest = null;
let generation = 0;
const pretty = value => value.replaceAll("_", " ");
function node(tag, text, className) {const el = document.createElement(tag); if(text !== undefined) el.textContent = text; if(className) el.className = className; return el;}
function resetResult(){generation++; currentResult=null; $("analysis-result").classList.add("hidden");$("empty-state").classList.remove("hidden");$("error-panel").classList.add("hidden");$("evidence-step").classList.remove("active");$("review-step").classList.remove("active");}
function loadRequest(req){resetResult();activeRequestId=req.request_id;$("request-meta").textContent=req.request_id === "REQ-CUSTOM" ? "New request · incomplete fields can be clarified" : req.request_id+" · edit before analysis";
  $("requester").value=req.requester_id||"";for(const [id,key] of [["product","product_name"],["vendor","vendor_name"],["category","category"],["cost","annual_cost_usd"],["users","user_count"],["purpose","business_justification"],["data-level","data_access_level"]]) $(id).value=req[key]??"";
  if(!$("data-level").value) $("data-level").value="unknown";
  $("integrations").value=(req.requested_integrations||[]).join("\n");
  for(const el of document.querySelectorAll(".request-item")) {el.classList.toggle("selected",el.dataset.id===activeRequestId);el.setAttribute("aria-current",el.dataset.id===activeRequestId?"true":"false");}
}
function readRequest(){return {request_id:activeRequestId,requester_id:$("requester").value,product_name:$("product").value.trim(),vendor_name:$("vendor").value.trim(),category:$("category").value.trim(),annual_cost_usd:$("cost").value===""?null:Number($("cost").value),user_count:$("users").value===""?null:Number($("users").value),business_justification:$("purpose").value.trim(),data_access_level:$("data-level").value,requested_integrations:$("integrations").value.split("\n").map(s=>s.trim()).filter(Boolean),urgency:"normal"};}
function updateMode(){const live=$("mode").value==="live";$("mode-banner").replaceChildren(node("span","i","banner-icon"),node("span",live?"Live AI · Evidence is analyzed by the configured model. Human approval is always required.":"Offline demo · Analysis uses a deterministic simulation. Live AI is available when configured."));}
function renderResult(result){currentResult=result;$("empty-state").classList.add("hidden");$("analysis-result").classList.remove("hidden");$("evidence-step").classList.add("active");$("review-step").classList.add("active");
  for(const [id,key] of [["recommendation","recommendation"],["rationale","rationale"],["next-step","next_step"]]) $(id).textContent=result[key];
  const tel=result.telemetry||{};$("result-mode").textContent=tel.mode==="live"?"LIVE AI":"OFFLINE DEMO";$("metrics").replaceChildren(...[`${result.architecture==="single"?"Architecture A":"Architecture B"}`,`${Math.round(tel.latency_ms||0)} ms`,`${tel.tool_calls||0} tools`,`${tel.llm_calls||0} LLM calls`].map(s=>node("span",s)));
  $("approvals").replaceChildren(...result.required_approvals.map(s=>node("span",s,"pill")));
  $("missing-section").classList.toggle("hidden",result.missing_information.length===0);$("missing-list").replaceChildren(...result.missing_information.map(s=>node("li",s)));
  $("risks").replaceChildren(...(result.risk_flags.length?result.risk_flags.map(s=>node("span",pretty(s),"pill risk")):[node("span","No policy risk flags found.","no-flags")]));
  $("evidence-count").textContent=`${result.evidence.length} FACTS`;
  $("evidence-list").replaceChildren(...result.evidence.map(e=>{const el=node("article",undefined,"evidence-item");const meta=node("div",undefined,"evidence-meta");meta.append(node("span",pretty(e.source).toUpperCase()),node("span",e.evidence_id||"","evidence-id"));el.append(meta,node("p",e.finding),node("div",e.reference||"","evidence-ref"));return el;}));
  $("stage-details").replaceChildren(node("p",`Stages: ${(tel.agent_stages||[]).map(pretty).join(" → ")}. Policy ${result.policy_version}, snapshot ${result.reference_date}. All reviews remain pending.`,"stage-detail"));
  $("tool-trace").replaceChildren(...(tel.tool_trace||[]).map(t=>node("div",`${pretty(t.name)} · ${t.status} · ${t.latency_ms} ms`,"tool-trace-row")));
  $("raw-result").textContent=JSON.stringify(result,null,2);
}
$("request-form").addEventListener("submit",async event=>{event.preventDefault();const run=++generation;const request=readRequest();const button=$("analyze-button");button.disabled=true;button.firstElementChild.textContent="Gathering evidence…";$("result-column").setAttribute("aria-busy","true");$("error-panel").classList.add("hidden");
  try {const response=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({request,architecture:$("architecture").value,mode:$("mode").value})});const payload=await response.json();if(!response.ok){const message=typeof payload.detail==="string"?payload.detail:"Please check cost, license count, and input lengths, then try again.";throw new Error(message);}if(run===generation){analyzedRequest=request;renderResult(payload);}}
  catch(error){if(run===generation){$("error-panel").textContent=error.message||"Analysis failed. Please try again.";$("error-panel").classList.remove("hidden");}}
  finally{button.disabled=false;button.firstElementChild.textContent="Analyze request";$("result-column").setAttribute("aria-busy","false");}
});
$("handoff-button").addEventListener("click",()=>{if(!currentResult)return;const packageData={handoff_status:"prepared_for_human_review",purchase_authorized:false,created_at:new Date().toISOString(),request:analyzedRequest,decision:currentResult,reviewers:currentResult.required_approvals.map(role=>({role,status:"pending"}))};const blob=new Blob([JSON.stringify(packageData,null,2)],{type:"application/json"});const url=URL.createObjectURL(blob);const a=node("a");a.href=url;a.download=`${currentResult.request_id.replace(/[^a-zA-Z0-9_-]/g,"_")}-human-review.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$("new-request").addEventListener("click",()=>loadRequest({request_id:"REQ-CUSTOM",data_access_level:"unknown"}));
$("request-form").addEventListener("input",resetResult);
$("architecture").addEventListener("change",resetResult);
$("mode").addEventListener("change",()=>{resetResult();updateMode();});
async function init(){try{const response=await fetch("/api/bootstrap");if(!response.ok)throw new Error("Unable to load the workspace.");bootstrap=await response.json();$("request-count").textContent=bootstrap.requests.length;
  $("requester").replaceChildren(node("option","Select requester"));$("requester").firstElementChild.value="";
  for(const employee of bootstrap.employees){const option=node("option",`${employee.name} · ${employee.department}`);option.value=employee.employee_id;$("requester").append(option);}
  for(const req of bootstrap.requests){const button=node("button",undefined,"request-item");button.type="button";button.dataset.id=req.request_id;button.append(node("strong",req.product_name),node("small",`${req.request_id} · ${req.annual_cost_usd===null?"Cost not provided":new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0}).format(req.annual_cost_usd)}`));button.addEventListener("click",()=>loadRequest(req));$("request-list").append(button);}
  $("mode").querySelector('[value="live"]').disabled=!bootstrap.live_available;$("mode").value=bootstrap.live_available&&bootstrap.default_mode==="live"?"live":"offline";updateMode();loadRequest(bootstrap.requests[0]);
}catch(error){$("error-panel").textContent=error.message;$("error-panel").classList.remove("hidden");$("analyze-button").disabled=true;}}
init();
