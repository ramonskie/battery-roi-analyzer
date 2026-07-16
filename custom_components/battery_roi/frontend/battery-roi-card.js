var T=globalThis,L=T.ShadowRoot&&(T.ShadyCSS===void 0||T.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,j=Symbol(),Q=new WeakMap,C=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==j)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(L&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=Q.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&Q.set(e,t))}return t}toString(){return this.cssText}},tt=a=>new C(typeof a=="string"?a:a+"",void 0,j),I=(a,...t)=>{let e=a.length===1?a[0]:t.reduce((s,i,r)=>s+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+a[r+1],a[0]);return new C(e,a,j)},et=(a,t)=>{if(L)a.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),i=T.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,a.appendChild(s)}},B=L?a=>a:a=>a instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return tt(e)})(a):a;var{is:ft,defineProperty:gt,getOwnPropertyDescriptor:yt,getOwnPropertyNames:$t,getOwnPropertySymbols:xt,getPrototypeOf:At}=Object,f=globalThis,st=f.trustedTypes,wt=st?st.emptyScript:"",St=f.reactiveElementPolyfillSupport,k=(a,t)=>a,W={toAttribute(a,t){switch(t){case Boolean:a=a?wt:null;break;case Object:case Array:a=a==null?a:JSON.stringify(a)}return a},fromAttribute(a,t){let e=a;switch(t){case Boolean:e=a!==null;break;case Number:e=a===null?null:Number(a);break;case Object:case Array:try{e=JSON.parse(a)}catch{e=null}}return e}},rt=(a,t)=>!ft(a,t),it={attribute:!0,type:String,converter:W,reflect:!1,useDefault:!1,hasChanged:rt};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),f.litPropertyMetadata??(f.litPropertyMetadata=new WeakMap);var v=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??(this.l=[])).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=it){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&gt(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){let{get:i,set:r}=yt(this.prototype,t)??{get(){return this[e]},set(n){this[e]=n}};return{get:i,set(n){let l=i?.call(this);r?.call(this,n),this.requestUpdate(t,l,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??it}static _$Ei(){if(this.hasOwnProperty(k("elementProperties")))return;let t=At(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(k("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(k("properties"))){let e=this.properties,s=[...$t(e),...xt(e)];for(let i of s)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)e.unshift(B(i))}else t!==void 0&&e.push(B(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??(this._$EO=new Set)).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return et(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let r=(s.converter?.toAttribute!==void 0?s.converter:W).toAttribute(e,s.type);this._$Em=t,r==null?this.removeAttribute(i):this.setAttribute(i,r),this._$Em=null}}_$AK(t,e){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let r=s.getPropertyOptions(i),n=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:W;this._$Em=i;let l=n.fromAttribute(e,r.type);this[i]=l??this._$Ej?.get(i)??l,this._$Em=null}}requestUpdate(t,e,s,i=!1,r){if(t!==void 0){let n=this.constructor;if(i===!1&&(r=this[t]),s??(s=n.getPropertyOptions(t)),!((s.hasChanged??rt)(r,e)||s.useDefault&&s.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(n._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:r},n){s&&!(this._$Ej??(this._$Ej=new Map)).has(t)&&(this._$Ej.set(t,n??e??this[t]),r!==!0||n!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??(this._$Eq=new Set)).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(let[i,r]of this._$Ep)this[i]=r;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,r]of s){let{wrapped:n}=r,l=this[i];n!==!0||this._$AL.has(i)||l===void 0||this.C(i,void 0,r,l)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&(this._$Eq=this._$Eq.forEach(e=>this._$ET(e,this[e]))),this._$EM()}updated(t){}firstUpdated(t){}};v.elementStyles=[],v.shadowRootOptions={mode:"open"},v[k("elementProperties")]=new Map,v[k("finalized")]=new Map,St?.({ReactiveElement:v}),(f.reactiveElementVersions??(f.reactiveElementVersions=[])).push("2.1.2");var N=globalThis,at=a=>a,D=N.trustedTypes,nt=D?D.createPolicy("lit-html",{createHTML:a=>a}):void 0,pt="$lit$",g=`lit$${Math.random().toFixed(9).slice(2)}$`,ut="?"+g,Et=`<${ut}>`,A=document,O=()=>A.createComment(""),U=a=>a===null||typeof a!="object"&&typeof a!="function",X=Array.isArray,Ct=a=>X(a)||typeof a?.[Symbol.iterator]=="function",q=`[ 	
\f\r]`,P=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ot=/-->/g,lt=/>/g,$=RegExp(`>|${q}(?:([^\\s"'>=/]+)(${q}*=${q}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ct=/'/g,dt=/"/g,_t=/^(?:script|style|textarea|title)$/i,Z=a=>(t,...e)=>({_$litType$:a,strings:t,values:e}),_=Z(1),Lt=Z(2),Dt=Z(3),w=Symbol.for("lit-noChange"),h=Symbol.for("lit-nothing"),ht=new WeakMap,x=A.createTreeWalker(A,129);function bt(a,t){if(!X(a)||!a.hasOwnProperty("raw"))throw Error("invalid template strings array");return nt!==void 0?nt.createHTML(t):t}var kt=(a,t)=>{let e=a.length-1,s=[],i,r=t===2?"<svg>":t===3?"<math>":"",n=P;for(let l=0;l<e;l++){let o=a[l],d,p,c=-1,b=0;for(;b<o.length&&(n.lastIndex=b,p=n.exec(o),p!==null);)b=n.lastIndex,n===P?p[1]==="!--"?n=ot:p[1]!==void 0?n=lt:p[2]!==void 0?(_t.test(p[2])&&(i=RegExp("</"+p[2],"g")),n=$):p[3]!==void 0&&(n=$):n===$?p[0]===">"?(n=i??P,c=-1):p[1]===void 0?c=-2:(c=n.lastIndex-p[2].length,d=p[1],n=p[3]===void 0?$:p[3]==='"'?dt:ct):n===dt||n===ct?n=$:n===ot||n===lt?n=P:(n=$,i=void 0);let m=n===$&&a[l+1].startsWith("/>")?" ":"";r+=n===P?o+Et:c>=0?(s.push(d),o.slice(0,c)+pt+o.slice(c)+g+m):o+g+(c===-2?l:m)}return[bt(a,r+(a[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},M=class a{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let r=0,n=0,l=t.length-1,o=this.parts,[d,p]=kt(t,e);if(this.el=a.createElement(d,s),x.currentNode=this.el.content,e===2||e===3){let c=this.el.content.firstChild;c.replaceWith(...c.childNodes)}for(;(i=x.nextNode())!==null&&o.length<l;){if(i.nodeType===1){if(i.hasAttributes())for(let c of i.getAttributeNames())if(c.endsWith(pt)){let b=p[n++],m=i.getAttribute(c).split(g),H=/([.?@])?(.*)/.exec(b);o.push({type:1,index:r,name:H[2],strings:m,ctor:H[1]==="."?F:H[1]==="?"?K:H[1]==="@"?Y:E}),i.removeAttribute(c)}else c.startsWith(g)&&(o.push({type:6,index:r}),i.removeAttribute(c));if(_t.test(i.tagName)){let c=i.textContent.split(g),b=c.length-1;if(b>0){i.textContent=D?D.emptyScript:"";for(let m=0;m<b;m++)i.append(c[m],O()),x.nextNode(),o.push({type:2,index:++r});i.append(c[b],O())}}}else if(i.nodeType===8)if(i.data===ut)o.push({type:2,index:r});else{let c=-1;for(;(c=i.data.indexOf(g,c+1))!==-1;)o.push({type:7,index:r}),c+=g.length-1}r++}}static createElement(t,e){let s=A.createElement("template");return s.innerHTML=t,s}};function S(a,t,e=a,s){if(t===w)return t;let i=s!==void 0?e._$Co?.[s]:e._$Cl,r=U(t)?void 0:t._$litDirective$;return i?.constructor!==r&&(i?._$AO?.(!1),r===void 0?i=void 0:(i=new r(a),i._$AT(a,e,s)),s!==void 0?(e._$Co??(e._$Co=[]))[s]=i:e._$Cl=i),i!==void 0&&(t=S(a,i._$AS(a,t.values),i,s)),t}var V=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??A).importNode(e,!0);x.currentNode=i;let r=x.nextNode(),n=0,l=0,o=s[0];for(;o!==void 0;){if(n===o.index){let d;o.type===2?d=new R(r,r.nextSibling,this,t):o.type===1?d=new o.ctor(r,o.name,o.strings,this,t):o.type===6&&(d=new J(r,this,t)),this._$AV.push(d),o=s[++l]}n!==o?.index&&(r=x.nextNode(),n++)}return x.currentNode=A,i}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},R=class a{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=h,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=S(this,t,e),U(t)?t===h||t==null||t===""?(this._$AH!==h&&this._$AR(),this._$AH=h):t!==this._$AH&&t!==w&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Ct(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==h&&U(this._$AH)?this._$AA.nextSibling.data=t:this.T(A.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=M.createElement(bt(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{let r=new V(i,this),n=r.u(this.options);r.p(e),this.T(n),this._$AH=r}}_$AC(t){let e=ht.get(t.strings);return e===void 0&&ht.set(t.strings,e=new M(t)),e}k(t){X(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,i=0;for(let r of t)i===e.length?e.push(s=new a(this.O(O()),this.O(O()),this,this.options)):s=e[i],s._$AI(r),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=at(t).nextSibling;at(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},E=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,r){this.type=1,this._$AH=h,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=r,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=h}_$AI(t,e=this,s,i){let r=this.strings,n=!1;if(r===void 0)t=S(this,t,e,0),n=!U(t)||t!==this._$AH&&t!==w,n&&(this._$AH=t);else{let l=t,o,d;for(t=r[0],o=0;o<r.length-1;o++)d=S(this,l[s+o],e,o),d===w&&(d=this._$AH[o]),n||(n=!U(d)||d!==this._$AH[o]),d===h?t=h:t!==h&&(t+=(d??"")+r[o+1]),this._$AH[o]=d}n&&!i&&this.j(t)}j(t){t===h?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},F=class extends E{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===h?void 0:t}},K=class extends E{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==h)}},Y=class extends E{constructor(t,e,s,i,r){super(t,e,s,i,r),this.type=5}_$AI(t,e=this){if((t=S(this,t,e,0)??h)===w)return;let s=this._$AH,i=t===h&&s!==h||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,r=t!==h&&(s===h||i);i&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},J=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){S(this,t)}};var Pt=N.litHtmlPolyfillSupport;Pt?.(M,R),(N.litHtmlVersions??(N.litHtmlVersions=[])).push("3.3.3");var vt=(a,t,e)=>{let s=e?.renderBefore??t,i=s._$litPart$;if(i===void 0){let r=e?.renderBefore??null;s._$litPart$=i=new R(t.insertBefore(O(),r),r,void 0,e??{})}return i._$AI(a),i};var z=globalThis,y=class extends v{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var e;let t=super.createRenderRoot();return(e=this.renderOptions).renderBefore??(e.renderBefore=t.firstChild),t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=vt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return w}};y._$litElement$=!0,y.finalized=!0,z.litElementHydrateSupport?.({LitElement:y});var Nt=z.litElementPolyfillSupport;Nt?.({LitElement:y});(z.litElementVersions??(z.litElementVersions=[])).push("4.2.2");var Ot="1.0.0";function u(a,t=1){let e=Number(a);return Number.isFinite(e)?e.toFixed(t):"\u2014"}function mt(a){let t=Number(a);return Number.isFinite(t)?(t<0?"\u2212\u20AC":"\u20AC")+Math.abs(t).toLocaleString("nl-NL",{minimumFractionDigits:0,maximumFractionDigits:0}):"\u2014"}function Ut(a){let t=Number(a);return Number.isFinite(t)?`${u(t,1)}%`:"\u2014"}function Mt(a){return a===!0||a==="true"?"\u2713 Yes":a===!1||a==="false"?"\u2717 No":"\u2014"}var G=class extends y{static get properties(){return{hass:{},config:{}}}static getStubConfig(){return{}}get _s(){let t=this.config.entity_prefix||"sensor.battery_roi",e=(s,i)=>this.config[`${s}_entity`]||`${t}_${i}`;return{best_size:e("best_size","best_size"),payback:e("payback","payback"),annual_saving:e("annual_saving","annual_saving"),best_capacity:e("best_capacity","best_capacity"),cycles:e("cycles","cycles"),self_consumption:e("self_consumption","self_consumption"),import_saved:e("import_saved","import_saved"),export_saved:e("export_saved","export_saved")}}_st(t){return this.hass?.states?.[t]}static get styles(){return I`
      :host {
        --br-grid-gap: 12px;
        --br-radius: 12px;
        --br-card-bg: var(--paper-card-background-color, #fff);
        --br-text: var(--primary-text-color, #1c1c1c);
        --br-text-secondary: var(--secondary-text-color, #727272);
        --br-accent: var(--accent-color, #ff7300);
        --br-green: #43a047;
        --br-red: #e53935;
        --br-border: var(--divider-color, #e0e0e0);
        display: block;
        font-family: var(--paper-font-body_-_font-family, inherit);
      }

      .card {
        background: var(--br-card-bg);
        border-radius: var(--br-radius);
        padding: 16px;
        box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0, 0, 0, 0.08));
      }

      /* ---- header ---- */
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--br-border);
      }
      .header h2 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: var(--br-text);
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .header .version {
        font-size: 11px;
        color: var(--br-text-secondary);
        background: var(--br-border);
        padding: 2px 6px;
        border-radius: 4px;
      }
      .header .updated {
        font-size: 12px;
        color: var(--br-text-secondary);
      }

      /* ---- stat grid ---- */
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
        gap: var(--br-grid-gap);
        margin-bottom: 16px;
      }
      .stat {
        background: var(--br-border);
        border-radius: var(--br-radius);
        padding: 12px;
        text-align: center;
        transition: transform 0.15s;
      }
      .stat:hover {
        transform: translateY(-2px);
      }
      .stat .value {
        font-size: 22px;
        font-weight: 700;
        color: var(--br-text);
        line-height: 1.2;
      }
      .stat .value.green {
        color: var(--br-green);
      }
      .stat .value.red {
        color: var(--br-red);
      }
      .stat .value.accent {
        color: var(--br-accent);
      }
      .stat .label {
        font-size: 11px;
        color: var(--br-text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
      }

      /* ---- section ---- */
      .section-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--br-text);
        margin: 20px 0 12px;
        padding-bottom: 6px;
        border-bottom: 1px solid var(--br-border);
      }

      /* ---- capacity bar chart ---- */
      .chart-wrap {
        overflow-x: auto;
        padding: 4px 0 8px;
      }
      .chart-table {
        width: 100%;
        border-collapse: collapse;
        min-width: 420px;
      }
      .chart-table th {
        text-align: left;
        font-size: 11px;
        color: var(--br-text-secondary);
        padding: 0 0 4px 0;
        font-weight: 500;
      }
      .chart-table td {
        padding: 2px 0;
        vertical-align: middle;
      }
      .chart-table .cap-label {
        font-size: 12px;
        font-weight: 600;
        color: var(--br-text);
        width: 40px;
        white-space: nowrap;
      }
      .bar-track {
        background: var(--br-border);
        border-radius: 4px;
        height: 18px;
        position: relative;
        overflow: hidden;
      }
      .bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.4s ease;
        min-width: 2px;
      }
      .bar-fill.annual {
        background: var(--br-accent);
      }
      .bar-fill.payback {
        background: var(--br-green);
      }
      .bar-fill.payback.overshoot {
        background: var(--br-red);
      }
      .bar-val {
        font-size: 11px;
        color: var(--br-text-secondary);
        padding-left: 8px;
        white-space: nowrap;
      }
      .chart-legend {
        display: flex;
        gap: 16px;
        font-size: 11px;
        color: var(--br-text-secondary);
        margin-top: 6px;
      }
      .chart-legend .dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 3px;
        margin-right: 4px;
        vertical-align: middle;
      }

      /* ---- monthly heatmap ---- */
      .heatmap {
        display: grid;
        grid-template-columns: 60px repeat(auto-fill, minmax(28px, 1fr));
        gap: 2px;
        align-items: end;
        margin-top: 6px;
      }
      .heatmap .hm-label {
        font-size: 10px;
        color: var(--br-text-secondary);
        text-align: right;
        padding-right: 6px;
        line-height: 28px;
      }
      .hm-cell {
        width: 100%;
        aspect-ratio: 1;
        border-radius: 3px;
        position: relative;
        cursor: pointer;
      }
      .hm-cell:hover::after {
        content: attr(data-tooltip);
        position: absolute;
        bottom: 110%;
        left: 50%;
        transform: translateX(-50%);
        background: var(--br-text);
        color: var(--br-card-bg);
        font-size: 10px;
        padding: 3px 6px;
        border-radius: 4px;
        white-space: nowrap;
        z-index: 10;
        pointer-events: none;
      }
      .hm-legend {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 10px;
        color: var(--br-text-secondary);
        margin-top: 8px;
        justify-content: flex-end;
      }
      .hm-legend .hm-swatch {
        width: 14px;
        height: 14px;
        border-radius: 2px;
        display: inline-block;
      }

      /* ---- lifecycle info ---- */
      .lifecycle {
        font-size: 12px;
        color: var(--br-text-secondary);
        margin-top: 12px;
        padding-top: 10px;
        border-top: 1px solid var(--br-border);
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
      }
    `}render(){let t=this._s,e=this._st(t.best_size),s=this._st(t.payback),i=this._st(t.annual_saving),r=e?.attributes?.by_capacity,n=e?.attributes?.monthly_data,l=s?.attributes||{},o=s?.state,d=l.within_lifetime;return _`
      <ha-card class="card">
        ${this._render_header(e)}
        ${this._render_stats(o,l,i)}
        ${this._render_secondary_stats(t)}
        ${r?this._render_chart(r):""}
        ${n?this._render_heatmap(n):""}
        ${this._render_lifecycle(l)}
      </ha-card>
    `}_render_header(t){let e=t?.last_updated?new Date(t.last_updated).toLocaleString("nl-NL",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}):"";return _`
      <div class="header">
        <h2>
          <span>⚡ Battery ROI</span>
          <span class="version">v${Ot}</span>
        </h2>
        <span class="updated">${e}</span>
      </div>
    `}_render_stats(t,e,s){let i=u(t,1),n=e.within_lifetime?"green":"red",l=s?.state??"\u2014",o=Number(e.net_saving_eur)>=0?"green":"red";return _`
      <div class="grid">
        <div class="stat">
          <div class="value accent">
            ${u(this._st(this._s.best_size)?.state,1)}
          </div>
          <div class="label">Best Size (kWh)</div>
        </div>
        <div class="stat">
          <div class="value ${n}">${i}</div>
          <div class="label">Payback (yr)</div>
        </div>
        <div class="stat">
          <div class="value green">€${u(l,0)}</div>
          <div class="label">Annual Saving</div>
        </div>
        <div class="stat">
          <div class="value ${o}">
            ${mt(e.net_saving_eur)}
          </div>
          <div class="label">Net Result (life)</div>
        </div>
      </div>
    `}_render_secondary_stats(t){return _`
      <div class="grid">
        <div class="stat">
          <div class="value">${Ut(this._st(t.self_consumption)?.state)}</div>
          <div class="label">Self-Consumption</div>
        </div>
        <div class="stat">
          <div class="value">${u(this._st(t.cycles)?.state,1)}</div>
          <div class="label">Cycles / Year</div>
        </div>
        <div class="stat">
          <div class="value">${u(this._st(t.import_saved)?.state,0)}</div>
          <div class="label">Import Saved (kWh/yr)</div>
        </div>
        <div class="stat">
          <div class="value">${u(this._st(t.export_saved)?.state,0)}</div>
          <div class="label">Export Saved (kWh/yr)</div>
        </div>
      </div>
    `}_render_chart(t){let e=Object.entries(t).map(([r,n])=>({cap:r.replace("_","."),...n})).sort((r,n)=>Number(r.cap)-Number(n.cap)),s=Math.max(...e.map(r=>r.payback_years!=null?r.payback_years:0),1),i=Math.max(...e.map(r=>r.annual_saving_eur??0),1);return _`
      <div class="section-title">Capacity Comparison</div>
      <div class="chart-wrap">
        <table class="chart-table">
          <thead>
            <tr>
              <th>kWh</th>
              <th>Annual Saving</th>
              <th></th>
              <th>Payback</th>
              <th></th>
              <th>ROI</th>
            </tr>
          </thead>
          <tbody>
            ${e.map(r=>_`
                <tr>
                  <td class="cap-label">${r.cap}</td>
                  <td style="width:35%">
                    <div class="bar-track">
                      <div
                        class="bar-fill annual"
                        style="width:${(r.annual_saving_eur??0)/i*100}%"
                      ></div>
                    </div>
                  </td>
                  <td class="bar-val">
                    €${u(r.annual_saving_eur,0)}
                  </td>
                  <td style="width:35%">
                    <div class="bar-track">
                      <div
                        class="bar-fill payback ${r.payback_years!=null&&r.payback_years>20?"overshoot":""}"
                        style="width:${Math.min((r.payback_years??s)/s*100,100)}%"
                      ></div>
                    </div>
                  </td>
                  <td class="bar-val">
                    ${r.payback_years!=null?`${u(r.payback_years,1)} yr`:"\u221E"}
                  </td>
                  <td class="bar-val">
                    ${r.roi_pct!=null?`${u(r.roi_pct,1)}%`:"\u2014"}
                  </td>
                </tr>
              `)}
          </tbody>
        </table>
      </div>
      <div class="chart-legend">
        <span><span class="dot" style="background:var(--br-accent)"></span>Annual Saving</span>
        <span><span class="dot" style="background:var(--br-green)"></span>Payback</span>
      </div>
    `}_render_heatmap(t){let e=Object.entries(t).sort(([r],[n])=>r.localeCompare(n)),s=Math.max(...e.map(([,r])=>Math.max(r.battery_out_kwh??0,r.battery_in_kwh??0)),1),i=r=>Math.min(Math.round((r??0)/s*10),10);return _`
      <div class="section-title">Monthly Battery Usage (kWh)</div>
      <div class="heatmap">
        <span class="hm-label"></span>
        <span class="hm-label" style="text-align:center">In</span>
        <span class="hm-label" style="text-align:center">Out</span>
        ${e.map(([r,n])=>_`
            <span class="hm-label">${r}</span>
            <div
              class="hm-cell"
              style="background:var(--br-accent);opacity:${.1+i(n.battery_in_kwh)*.08}"
              data-tooltip="${r} in: ${u(n.battery_in_kwh,0)} kWh"
            ></div>
            <div
              class="hm-cell"
              style="background:var(--br-green);opacity:${.1+i(n.battery_out_kwh)*.08}"
              data-tooltip="${r} out: ${u(n.battery_out_kwh,0)} kWh"
            ></div>
          `)}
      </div>
      <div class="hm-legend">
        <span class="hm-swatch" style="background:var(--br-accent);opacity:0.8"></span> Charged
        <span class="hm-swatch" style="background:var(--br-green);opacity:0.8"></span> Discharged
        <span style="margin-left:auto">Low ▸ High</span>
      </div>
    `}_render_lifecycle(t){let e=t.upfront_cost_eur,s=t.within_lifetime;return _`
      <div class="lifecycle">
        <span>Upfront: ${e!=null?mt(e):"\u2014"}</span>
        <span>Pays back within life: ${Mt(s)}</span>
        <span>Annual: €${u(t.annual_saving_eur,0)}</span>
      </div>
    `}static async getConfigElement(){let t=document.createElement("div");return t.innerHTML=`
      <style>
        .br-edit { padding: 8px; }
        .br-edit label { display:block; margin:8px 0 4px; font-size:12px; color:var(--secondary-text-color); }
        .br-edit input { width:100%; box-sizing:border-box; }
      </style>
      <div class="br-edit">
        <label>Title (optional)</label>
        <input id="title" placeholder="Battery ROI" />
        <label>Entity prefix (default: sensor.battery_roi)</label>
        <input id="prefix" placeholder="sensor.battery_roi" />
      </div>
    `,t.querySelector("#title").addEventListener("change",()=>{t._config={...t._config,title:t.querySelector("#title").value||void 0},t.dispatchEvent(new Event("config-changed",{bubbles:!0}))}),t.querySelector("#prefix").addEventListener("change",()=>{t._config={...t._config,entity_prefix:t.querySelector("#prefix").value||void 0},t.dispatchEvent(new Event("config-changed",{bubbles:!0}))}),t.setConfig=e=>{t._config=e,t.querySelector("#title").value=e?.title||"",t.querySelector("#prefix").value=e?.entity_prefix||""},t}};customElements.define("battery-roi-card",G);window.customCards=window.customCards||[];window.customCards.push({type:"battery-roi-card",name:"Battery ROI Analyzer",description:"Dashboard card showing battery ROI metrics, capacity comparison, and monthly usage heatmap",preview:!0,documentationURL:"https://github.com/ramonskie/battery-roi-analyzer"});
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
