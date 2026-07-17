(() => {
  // node_modules/@lit/reactive-element/css-tag.js
  var t = globalThis;
  var e = t.ShadowRoot && (void 0 === t.ShadyCSS || t.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype;
  var s = /* @__PURE__ */ Symbol();
  var o = /* @__PURE__ */ new WeakMap();
  var n = class {
    constructor(t3, e4, o5) {
      if (this._$cssResult$ = true, o5 !== s) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
      this.cssText = t3, this.t = e4;
    }
    get styleSheet() {
      let t3 = this.o;
      const s4 = this.t;
      if (e && void 0 === t3) {
        const e4 = void 0 !== s4 && 1 === s4.length;
        e4 && (t3 = o.get(s4)), void 0 === t3 && ((this.o = t3 = new CSSStyleSheet()).replaceSync(this.cssText), e4 && o.set(s4, t3));
      }
      return t3;
    }
    toString() {
      return this.cssText;
    }
  };
  var r = (t3) => new n("string" == typeof t3 ? t3 : t3 + "", void 0, s);
  var i = (t3, ...e4) => {
    const o5 = 1 === t3.length ? t3[0] : e4.reduce((e5, s4, o6) => e5 + ((t4) => {
      if (true === t4._$cssResult$) return t4.cssText;
      if ("number" == typeof t4) return t4;
      throw Error("Value passed to 'css' function must be a 'css' function result: " + t4 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
    })(s4) + t3[o6 + 1], t3[0]);
    return new n(o5, t3, s);
  };
  var S = (s4, o5) => {
    if (e) s4.adoptedStyleSheets = o5.map((t3) => t3 instanceof CSSStyleSheet ? t3 : t3.styleSheet);
    else for (const e4 of o5) {
      const o6 = document.createElement("style"), n4 = t.litNonce;
      void 0 !== n4 && o6.setAttribute("nonce", n4), o6.textContent = e4.cssText, s4.appendChild(o6);
    }
  };
  var c = e ? (t3) => t3 : (t3) => t3 instanceof CSSStyleSheet ? ((t4) => {
    let e4 = "";
    for (const s4 of t4.cssRules) e4 += s4.cssText;
    return r(e4);
  })(t3) : t3;

  // node_modules/@lit/reactive-element/reactive-element.js
  var { is: i2, defineProperty: e2, getOwnPropertyDescriptor: h, getOwnPropertyNames: r2, getOwnPropertySymbols: o2, getPrototypeOf: n2 } = Object;
  var a = globalThis;
  var c2 = a.trustedTypes;
  var l = c2 ? c2.emptyScript : "";
  var p = a.reactiveElementPolyfillSupport;
  var d = (t3, s4) => t3;
  var u = { toAttribute(t3, s4) {
    switch (s4) {
      case Boolean:
        t3 = t3 ? l : null;
        break;
      case Object:
      case Array:
        t3 = null == t3 ? t3 : JSON.stringify(t3);
    }
    return t3;
  }, fromAttribute(t3, s4) {
    let i5 = t3;
    switch (s4) {
      case Boolean:
        i5 = null !== t3;
        break;
      case Number:
        i5 = null === t3 ? null : Number(t3);
        break;
      case Object:
      case Array:
        try {
          i5 = JSON.parse(t3);
        } catch (t4) {
          i5 = null;
        }
    }
    return i5;
  } };
  var f = (t3, s4) => !i2(t3, s4);
  var b = { attribute: true, type: String, converter: u, reflect: false, useDefault: false, hasChanged: f };
  Symbol.metadata ?? (Symbol.metadata = /* @__PURE__ */ Symbol("metadata")), a.litPropertyMetadata ?? (a.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
  var y = class extends HTMLElement {
    static addInitializer(t3) {
      this._$Ei(), (this.l ?? (this.l = [])).push(t3);
    }
    static get observedAttributes() {
      return this.finalize(), this._$Eh && [...this._$Eh.keys()];
    }
    static createProperty(t3, s4 = b) {
      if (s4.state && (s4.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t3) && ((s4 = Object.create(s4)).wrapped = true), this.elementProperties.set(t3, s4), !s4.noAccessor) {
        const i5 = /* @__PURE__ */ Symbol(), h3 = this.getPropertyDescriptor(t3, i5, s4);
        void 0 !== h3 && e2(this.prototype, t3, h3);
      }
    }
    static getPropertyDescriptor(t3, s4, i5) {
      const { get: e4, set: r4 } = h(this.prototype, t3) ?? { get() {
        return this[s4];
      }, set(t4) {
        this[s4] = t4;
      } };
      return { get: e4, set(s5) {
        const h3 = e4?.call(this);
        r4?.call(this, s5), this.requestUpdate(t3, h3, i5);
      }, configurable: true, enumerable: true };
    }
    static getPropertyOptions(t3) {
      return this.elementProperties.get(t3) ?? b;
    }
    static _$Ei() {
      if (this.hasOwnProperty(d("elementProperties"))) return;
      const t3 = n2(this);
      t3.finalize(), void 0 !== t3.l && (this.l = [...t3.l]), this.elementProperties = new Map(t3.elementProperties);
    }
    static finalize() {
      if (this.hasOwnProperty(d("finalized"))) return;
      if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d("properties"))) {
        const t4 = this.properties, s4 = [...r2(t4), ...o2(t4)];
        for (const i5 of s4) this.createProperty(i5, t4[i5]);
      }
      const t3 = this[Symbol.metadata];
      if (null !== t3) {
        const s4 = litPropertyMetadata.get(t3);
        if (void 0 !== s4) for (const [t4, i5] of s4) this.elementProperties.set(t4, i5);
      }
      this._$Eh = /* @__PURE__ */ new Map();
      for (const [t4, s4] of this.elementProperties) {
        const i5 = this._$Eu(t4, s4);
        void 0 !== i5 && this._$Eh.set(i5, t4);
      }
      this.elementStyles = this.finalizeStyles(this.styles);
    }
    static finalizeStyles(s4) {
      const i5 = [];
      if (Array.isArray(s4)) {
        const e4 = new Set(s4.flat(1 / 0).reverse());
        for (const s5 of e4) i5.unshift(c(s5));
      } else void 0 !== s4 && i5.push(c(s4));
      return i5;
    }
    static _$Eu(t3, s4) {
      const i5 = s4.attribute;
      return false === i5 ? void 0 : "string" == typeof i5 ? i5 : "string" == typeof t3 ? t3.toLowerCase() : void 0;
    }
    constructor() {
      super(), this._$Ep = void 0, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
    }
    _$Ev() {
      this._$ES = new Promise((t3) => this.enableUpdating = t3), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((t3) => t3(this));
    }
    addController(t3) {
      (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(t3), void 0 !== this.renderRoot && this.isConnected && t3.hostConnected?.();
    }
    removeController(t3) {
      this._$EO?.delete(t3);
    }
    _$E_() {
      const t3 = /* @__PURE__ */ new Map(), s4 = this.constructor.elementProperties;
      for (const i5 of s4.keys()) this.hasOwnProperty(i5) && (t3.set(i5, this[i5]), delete this[i5]);
      t3.size > 0 && (this._$Ep = t3);
    }
    createRenderRoot() {
      const t3 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
      return S(t3, this.constructor.elementStyles), t3;
    }
    connectedCallback() {
      this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(true), this._$EO?.forEach((t3) => t3.hostConnected?.());
    }
    enableUpdating(t3) {
    }
    disconnectedCallback() {
      this._$EO?.forEach((t3) => t3.hostDisconnected?.());
    }
    attributeChangedCallback(t3, s4, i5) {
      this._$AK(t3, i5);
    }
    _$ET(t3, s4) {
      const i5 = this.constructor.elementProperties.get(t3), e4 = this.constructor._$Eu(t3, i5);
      if (void 0 !== e4 && true === i5.reflect) {
        const h3 = (void 0 !== i5.converter?.toAttribute ? i5.converter : u).toAttribute(s4, i5.type);
        this._$Em = t3, null == h3 ? this.removeAttribute(e4) : this.setAttribute(e4, h3), this._$Em = null;
      }
    }
    _$AK(t3, s4) {
      const i5 = this.constructor, e4 = i5._$Eh.get(t3);
      if (void 0 !== e4 && this._$Em !== e4) {
        const t4 = i5.getPropertyOptions(e4), h3 = "function" == typeof t4.converter ? { fromAttribute: t4.converter } : void 0 !== t4.converter?.fromAttribute ? t4.converter : u;
        this._$Em = e4;
        const r4 = h3.fromAttribute(s4, t4.type);
        this[e4] = r4 ?? this._$Ej?.get(e4) ?? r4, this._$Em = null;
      }
    }
    requestUpdate(t3, s4, i5, e4 = false, h3) {
      if (void 0 !== t3) {
        const r4 = this.constructor;
        if (false === e4 && (h3 = this[t3]), i5 ?? (i5 = r4.getPropertyOptions(t3)), !((i5.hasChanged ?? f)(h3, s4) || i5.useDefault && i5.reflect && h3 === this._$Ej?.get(t3) && !this.hasAttribute(r4._$Eu(t3, i5)))) return;
        this.C(t3, s4, i5);
      }
      false === this.isUpdatePending && (this._$ES = this._$EP());
    }
    C(t3, s4, { useDefault: i5, reflect: e4, wrapped: h3 }, r4) {
      i5 && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(t3) && (this._$Ej.set(t3, r4 ?? s4 ?? this[t3]), true !== h3 || void 0 !== r4) || (this._$AL.has(t3) || (this.hasUpdated || i5 || (s4 = void 0), this._$AL.set(t3, s4)), true === e4 && this._$Em !== t3 && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(t3));
    }
    async _$EP() {
      this.isUpdatePending = true;
      try {
        await this._$ES;
      } catch (t4) {
        Promise.reject(t4);
      }
      const t3 = this.scheduleUpdate();
      return null != t3 && await t3, !this.isUpdatePending;
    }
    scheduleUpdate() {
      return this.performUpdate();
    }
    performUpdate() {
      if (!this.isUpdatePending) return;
      if (!this.hasUpdated) {
        if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
          for (const [t5, s5] of this._$Ep) this[t5] = s5;
          this._$Ep = void 0;
        }
        const t4 = this.constructor.elementProperties;
        if (t4.size > 0) for (const [s5, i5] of t4) {
          const { wrapped: t5 } = i5, e4 = this[s5];
          true !== t5 || this._$AL.has(s5) || void 0 === e4 || this.C(s5, void 0, i5, e4);
        }
      }
      let t3 = false;
      const s4 = this._$AL;
      try {
        t3 = this.shouldUpdate(s4), t3 ? (this.willUpdate(s4), this._$EO?.forEach((t4) => t4.hostUpdate?.()), this.update(s4)) : this._$EM();
      } catch (s5) {
        throw t3 = false, this._$EM(), s5;
      }
      t3 && this._$AE(s4);
    }
    willUpdate(t3) {
    }
    _$AE(t3) {
      this._$EO?.forEach((t4) => t4.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t3)), this.updated(t3);
    }
    _$EM() {
      this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = false;
    }
    get updateComplete() {
      return this.getUpdateComplete();
    }
    getUpdateComplete() {
      return this._$ES;
    }
    shouldUpdate(t3) {
      return true;
    }
    update(t3) {
      this._$Eq && (this._$Eq = this._$Eq.forEach((t4) => this._$ET(t4, this[t4]))), this._$EM();
    }
    updated(t3) {
    }
    firstUpdated(t3) {
    }
  };
  y.elementStyles = [], y.shadowRootOptions = { mode: "open" }, y[d("elementProperties")] = /* @__PURE__ */ new Map(), y[d("finalized")] = /* @__PURE__ */ new Map(), p?.({ ReactiveElement: y }), (a.reactiveElementVersions ?? (a.reactiveElementVersions = [])).push("2.1.2");

  // node_modules/lit-html/lit-html.js
  var t2 = globalThis;
  var i3 = (t3) => t3;
  var s2 = t2.trustedTypes;
  var e3 = s2 ? s2.createPolicy("lit-html", { createHTML: (t3) => t3 }) : void 0;
  var h2 = "$lit$";
  var o3 = `lit$${Math.random().toFixed(9).slice(2)}$`;
  var n3 = "?" + o3;
  var r3 = `<${n3}>`;
  var l2 = document;
  var c3 = () => l2.createComment("");
  var a2 = (t3) => null === t3 || "object" != typeof t3 && "function" != typeof t3;
  var u2 = Array.isArray;
  var d2 = (t3) => u2(t3) || "function" == typeof t3?.[Symbol.iterator];
  var f2 = "[ 	\n\f\r]";
  var v = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g;
  var _ = /-->/g;
  var m = />/g;
  var p2 = RegExp(`>|${f2}(?:([^\\s"'>=/]+)(${f2}*=${f2}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g");
  var g = /'/g;
  var $ = /"/g;
  var y2 = /^(?:script|style|textarea|title)$/i;
  var x = (t3) => (i5, ...s4) => ({ _$litType$: t3, strings: i5, values: s4 });
  var b2 = x(1);
  var w = x(2);
  var T = x(3);
  var E = /* @__PURE__ */ Symbol.for("lit-noChange");
  var A = /* @__PURE__ */ Symbol.for("lit-nothing");
  var C = /* @__PURE__ */ new WeakMap();
  var P = l2.createTreeWalker(l2, 129);
  function V(t3, i5) {
    if (!u2(t3) || !t3.hasOwnProperty("raw")) throw Error("invalid template strings array");
    return void 0 !== e3 ? e3.createHTML(i5) : i5;
  }
  var N = (t3, i5) => {
    const s4 = t3.length - 1, e4 = [];
    let n4, l3 = 2 === i5 ? "<svg>" : 3 === i5 ? "<math>" : "", c4 = v;
    for (let i6 = 0; i6 < s4; i6++) {
      const s5 = t3[i6];
      let a3, u3, d3 = -1, f3 = 0;
      for (; f3 < s5.length && (c4.lastIndex = f3, u3 = c4.exec(s5), null !== u3); ) f3 = c4.lastIndex, c4 === v ? "!--" === u3[1] ? c4 = _ : void 0 !== u3[1] ? c4 = m : void 0 !== u3[2] ? (y2.test(u3[2]) && (n4 = RegExp("</" + u3[2], "g")), c4 = p2) : void 0 !== u3[3] && (c4 = p2) : c4 === p2 ? ">" === u3[0] ? (c4 = n4 ?? v, d3 = -1) : void 0 === u3[1] ? d3 = -2 : (d3 = c4.lastIndex - u3[2].length, a3 = u3[1], c4 = void 0 === u3[3] ? p2 : '"' === u3[3] ? $ : g) : c4 === $ || c4 === g ? c4 = p2 : c4 === _ || c4 === m ? c4 = v : (c4 = p2, n4 = void 0);
      const x2 = c4 === p2 && t3[i6 + 1].startsWith("/>") ? " " : "";
      l3 += c4 === v ? s5 + r3 : d3 >= 0 ? (e4.push(a3), s5.slice(0, d3) + h2 + s5.slice(d3) + o3 + x2) : s5 + o3 + (-2 === d3 ? i6 : x2);
    }
    return [V(t3, l3 + (t3[s4] || "<?>") + (2 === i5 ? "</svg>" : 3 === i5 ? "</math>" : "")), e4];
  };
  var S2 = class _S {
    constructor({ strings: t3, _$litType$: i5 }, e4) {
      let r4;
      this.parts = [];
      let l3 = 0, a3 = 0;
      const u3 = t3.length - 1, d3 = this.parts, [f3, v2] = N(t3, i5);
      if (this.el = _S.createElement(f3, e4), P.currentNode = this.el.content, 2 === i5 || 3 === i5) {
        const t4 = this.el.content.firstChild;
        t4.replaceWith(...t4.childNodes);
      }
      for (; null !== (r4 = P.nextNode()) && d3.length < u3; ) {
        if (1 === r4.nodeType) {
          if (r4.hasAttributes()) for (const t4 of r4.getAttributeNames()) if (t4.endsWith(h2)) {
            const i6 = v2[a3++], s4 = r4.getAttribute(t4).split(o3), e5 = /([.?@])?(.*)/.exec(i6);
            d3.push({ type: 1, index: l3, name: e5[2], strings: s4, ctor: "." === e5[1] ? I : "?" === e5[1] ? L : "@" === e5[1] ? z : H }), r4.removeAttribute(t4);
          } else t4.startsWith(o3) && (d3.push({ type: 6, index: l3 }), r4.removeAttribute(t4));
          if (y2.test(r4.tagName)) {
            const t4 = r4.textContent.split(o3), i6 = t4.length - 1;
            if (i6 > 0) {
              r4.textContent = s2 ? s2.emptyScript : "";
              for (let s4 = 0; s4 < i6; s4++) r4.append(t4[s4], c3()), P.nextNode(), d3.push({ type: 2, index: ++l3 });
              r4.append(t4[i6], c3());
            }
          }
        } else if (8 === r4.nodeType) if (r4.data === n3) d3.push({ type: 2, index: l3 });
        else {
          let t4 = -1;
          for (; -1 !== (t4 = r4.data.indexOf(o3, t4 + 1)); ) d3.push({ type: 7, index: l3 }), t4 += o3.length - 1;
        }
        l3++;
      }
    }
    static createElement(t3, i5) {
      const s4 = l2.createElement("template");
      return s4.innerHTML = t3, s4;
    }
  };
  function M(t3, i5, s4 = t3, e4) {
    if (i5 === E) return i5;
    let h3 = void 0 !== e4 ? s4._$Co?.[e4] : s4._$Cl;
    const o5 = a2(i5) ? void 0 : i5._$litDirective$;
    return h3?.constructor !== o5 && (h3?._$AO?.(false), void 0 === o5 ? h3 = void 0 : (h3 = new o5(t3), h3._$AT(t3, s4, e4)), void 0 !== e4 ? (s4._$Co ?? (s4._$Co = []))[e4] = h3 : s4._$Cl = h3), void 0 !== h3 && (i5 = M(t3, h3._$AS(t3, i5.values), h3, e4)), i5;
  }
  var R = class {
    constructor(t3, i5) {
      this._$AV = [], this._$AN = void 0, this._$AD = t3, this._$AM = i5;
    }
    get parentNode() {
      return this._$AM.parentNode;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    u(t3) {
      const { el: { content: i5 }, parts: s4 } = this._$AD, e4 = (t3?.creationScope ?? l2).importNode(i5, true);
      P.currentNode = e4;
      let h3 = P.nextNode(), o5 = 0, n4 = 0, r4 = s4[0];
      for (; void 0 !== r4; ) {
        if (o5 === r4.index) {
          let i6;
          2 === r4.type ? i6 = new k(h3, h3.nextSibling, this, t3) : 1 === r4.type ? i6 = new r4.ctor(h3, r4.name, r4.strings, this, t3) : 6 === r4.type && (i6 = new Z(h3, this, t3)), this._$AV.push(i6), r4 = s4[++n4];
        }
        o5 !== r4?.index && (h3 = P.nextNode(), o5++);
      }
      return P.currentNode = l2, e4;
    }
    p(t3) {
      let i5 = 0;
      for (const s4 of this._$AV) void 0 !== s4 && (void 0 !== s4.strings ? (s4._$AI(t3, s4, i5), i5 += s4.strings.length - 2) : s4._$AI(t3[i5])), i5++;
    }
  };
  var k = class _k {
    get _$AU() {
      return this._$AM?._$AU ?? this._$Cv;
    }
    constructor(t3, i5, s4, e4) {
      this.type = 2, this._$AH = A, this._$AN = void 0, this._$AA = t3, this._$AB = i5, this._$AM = s4, this.options = e4, this._$Cv = e4?.isConnected ?? true;
    }
    get parentNode() {
      let t3 = this._$AA.parentNode;
      const i5 = this._$AM;
      return void 0 !== i5 && 11 === t3?.nodeType && (t3 = i5.parentNode), t3;
    }
    get startNode() {
      return this._$AA;
    }
    get endNode() {
      return this._$AB;
    }
    _$AI(t3, i5 = this) {
      t3 = M(this, t3, i5), a2(t3) ? t3 === A || null == t3 || "" === t3 ? (this._$AH !== A && this._$AR(), this._$AH = A) : t3 !== this._$AH && t3 !== E && this._(t3) : void 0 !== t3._$litType$ ? this.$(t3) : void 0 !== t3.nodeType ? this.T(t3) : d2(t3) ? this.k(t3) : this._(t3);
    }
    O(t3) {
      return this._$AA.parentNode.insertBefore(t3, this._$AB);
    }
    T(t3) {
      this._$AH !== t3 && (this._$AR(), this._$AH = this.O(t3));
    }
    _(t3) {
      this._$AH !== A && a2(this._$AH) ? this._$AA.nextSibling.data = t3 : this.T(l2.createTextNode(t3)), this._$AH = t3;
    }
    $(t3) {
      const { values: i5, _$litType$: s4 } = t3, e4 = "number" == typeof s4 ? this._$AC(t3) : (void 0 === s4.el && (s4.el = S2.createElement(V(s4.h, s4.h[0]), this.options)), s4);
      if (this._$AH?._$AD === e4) this._$AH.p(i5);
      else {
        const t4 = new R(e4, this), s5 = t4.u(this.options);
        t4.p(i5), this.T(s5), this._$AH = t4;
      }
    }
    _$AC(t3) {
      let i5 = C.get(t3.strings);
      return void 0 === i5 && C.set(t3.strings, i5 = new S2(t3)), i5;
    }
    k(t3) {
      u2(this._$AH) || (this._$AH = [], this._$AR());
      const i5 = this._$AH;
      let s4, e4 = 0;
      for (const h3 of t3) e4 === i5.length ? i5.push(s4 = new _k(this.O(c3()), this.O(c3()), this, this.options)) : s4 = i5[e4], s4._$AI(h3), e4++;
      e4 < i5.length && (this._$AR(s4 && s4._$AB.nextSibling, e4), i5.length = e4);
    }
    _$AR(t3 = this._$AA.nextSibling, s4) {
      for (this._$AP?.(false, true, s4); t3 !== this._$AB; ) {
        const s5 = i3(t3).nextSibling;
        i3(t3).remove(), t3 = s5;
      }
    }
    setConnected(t3) {
      void 0 === this._$AM && (this._$Cv = t3, this._$AP?.(t3));
    }
  };
  var H = class {
    get tagName() {
      return this.element.tagName;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    constructor(t3, i5, s4, e4, h3) {
      this.type = 1, this._$AH = A, this._$AN = void 0, this.element = t3, this.name = i5, this._$AM = e4, this.options = h3, s4.length > 2 || "" !== s4[0] || "" !== s4[1] ? (this._$AH = Array(s4.length - 1).fill(new String()), this.strings = s4) : this._$AH = A;
    }
    _$AI(t3, i5 = this, s4, e4) {
      const h3 = this.strings;
      let o5 = false;
      if (void 0 === h3) t3 = M(this, t3, i5, 0), o5 = !a2(t3) || t3 !== this._$AH && t3 !== E, o5 && (this._$AH = t3);
      else {
        const e5 = t3;
        let n4, r4;
        for (t3 = h3[0], n4 = 0; n4 < h3.length - 1; n4++) r4 = M(this, e5[s4 + n4], i5, n4), r4 === E && (r4 = this._$AH[n4]), o5 || (o5 = !a2(r4) || r4 !== this._$AH[n4]), r4 === A ? t3 = A : t3 !== A && (t3 += (r4 ?? "") + h3[n4 + 1]), this._$AH[n4] = r4;
      }
      o5 && !e4 && this.j(t3);
    }
    j(t3) {
      t3 === A ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t3 ?? "");
    }
  };
  var I = class extends H {
    constructor() {
      super(...arguments), this.type = 3;
    }
    j(t3) {
      this.element[this.name] = t3 === A ? void 0 : t3;
    }
  };
  var L = class extends H {
    constructor() {
      super(...arguments), this.type = 4;
    }
    j(t3) {
      this.element.toggleAttribute(this.name, !!t3 && t3 !== A);
    }
  };
  var z = class extends H {
    constructor(t3, i5, s4, e4, h3) {
      super(t3, i5, s4, e4, h3), this.type = 5;
    }
    _$AI(t3, i5 = this) {
      if ((t3 = M(this, t3, i5, 0) ?? A) === E) return;
      const s4 = this._$AH, e4 = t3 === A && s4 !== A || t3.capture !== s4.capture || t3.once !== s4.once || t3.passive !== s4.passive, h3 = t3 !== A && (s4 === A || e4);
      e4 && this.element.removeEventListener(this.name, this, s4), h3 && this.element.addEventListener(this.name, this, t3), this._$AH = t3;
    }
    handleEvent(t3) {
      "function" == typeof this._$AH ? this._$AH.call(this.options?.host ?? this.element, t3) : this._$AH.handleEvent(t3);
    }
  };
  var Z = class {
    constructor(t3, i5, s4) {
      this.element = t3, this.type = 6, this._$AN = void 0, this._$AM = i5, this.options = s4;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AI(t3) {
      M(this, t3);
    }
  };
  var B = t2.litHtmlPolyfillSupport;
  B?.(S2, k), (t2.litHtmlVersions ?? (t2.litHtmlVersions = [])).push("3.3.3");
  var D = (t3, i5, s4) => {
    const e4 = s4?.renderBefore ?? i5;
    let h3 = e4._$litPart$;
    if (void 0 === h3) {
      const t4 = s4?.renderBefore ?? null;
      e4._$litPart$ = h3 = new k(i5.insertBefore(c3(), t4), t4, void 0, s4 ?? {});
    }
    return h3._$AI(t3), h3;
  };

  // node_modules/lit-element/lit-element.js
  var s3 = globalThis;
  var i4 = class extends y {
    constructor() {
      super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
    }
    createRenderRoot() {
      var _a;
      const t3 = super.createRenderRoot();
      return (_a = this.renderOptions).renderBefore ?? (_a.renderBefore = t3.firstChild), t3;
    }
    update(t3) {
      const r4 = this.render();
      this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t3), this._$Do = D(r4, this.renderRoot, this.renderOptions);
    }
    connectedCallback() {
      super.connectedCallback(), this._$Do?.setConnected(true);
    }
    disconnectedCallback() {
      super.disconnectedCallback(), this._$Do?.setConnected(false);
    }
    render() {
      return E;
    }
  };
  i4._$litElement$ = true, i4["finalized"] = true, s3.litElementHydrateSupport?.({ LitElement: i4 });
  var o4 = s3.litElementPolyfillSupport;
  o4?.({ LitElement: i4 });
  (s3.litElementVersions ?? (s3.litElementVersions = [])).push("4.2.2");

  // src/battery-roi-card.js
  console.log("[battery-roi] script loaded, LitElement:", typeof i4);
  var CARD_VERSION = "1.0.0";
  function _num(v2, decimals = 1) {
    const n4 = Number(v2);
    return Number.isFinite(n4) ? n4.toFixed(decimals) : "\u2014";
  }
  function _euro(v2) {
    const n4 = Number(v2);
    if (!Number.isFinite(n4)) return "\u2014";
    const prefix = n4 < 0 ? "\u2212\u20AC" : "\u20AC";
    return prefix + Math.abs(n4).toLocaleString("nl-NL", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    });
  }
  function _pct(v2) {
    const n4 = Number(v2);
    return Number.isFinite(n4) ? `${_num(n4, 1)}%` : "\u2014";
  }
  function _bool(v2) {
    if (v2 === true || v2 === "true") return "\u2713 Yes";
    if (v2 === false || v2 === "false") return "\u2717 No";
    return "\u2014";
  }
  var BatteryRoiCard = class extends i4 {
    static get properties() {
      return { hass: {}, config: {} };
    }
    static getStubConfig() {
      return {};
    }
    setConfig(config) {
      this.config = config;
      this._entityCache = null;
    }
    /* ----- auto-discover entities by scanning hass.states ------------ */
    _discoverEntities() {
      const explicit = {};
      for (const key of [
        "best_size",
        "payback",
        "annual_saving",
        "best_capacity",
        "cycles",
        "self_consumption",
        "import_saved",
        "export_saved"
      ]) {
        if (this.config[`${key}_entity`]) {
          explicit[key] = this.config[`${key}_entity`];
        }
      }
      const states = this.hass?.states || {};
      const prefix = this.config.entity_prefix || "sensor.battery_roi_analyzer";
      const candidates = Object.entries(states).filter(([eid]) => eid.startsWith(prefix)).map(([eid, st]) => ({ eid, ...st.attributes }));
      const byName = (name) => candidates.find(
        (c4) => c4.friendly_name === name || c4.friendly_name?.toLowerCase().includes(name.toLowerCase())
      );
      return {
        best_size: explicit.best_size || byName("Best size")?.eid || `${prefix}_best_size`,
        payback: explicit.payback || byName("Payback")?.eid || `${prefix}_payback`,
        annual_saving: explicit.annual_saving || byName("Annual saving")?.eid || `${prefix}_annual_saving`,
        best_capacity: explicit.best_capacity || byName("Best capacity (by NPV)")?.eid || `${prefix}_best_capacity`,
        cycles: explicit.cycles || byName("Cycles")?.eid || `${prefix}_cycles`,
        self_consumption: explicit.self_consumption || byName("Self-consumption")?.eid || `${prefix}_self_consumption`,
        import_saved: explicit.import_saved || byName("Import saved")?.eid || `${prefix}_import_saved`,
        export_saved: explicit.export_saved || byName("Export saved")?.eid || `${prefix}_export_saved`
      };
    }
    get _s() {
      const states = this.hass?.states || {};
      const key = Object.keys(states).filter((k2) => k2.startsWith("sensor.battery_roi_analyzer")).join(",");
      if (!this._entityCache || this._entityKey !== key) {
        this._entityKey = key;
        this._entityCache = this._discoverEntities();
      }
      return this._entityCache;
    }
    _st(id) {
      return this.hass?.states?.[id];
    }
    /* ----- styles ---------------------------------------------------- */
    static get styles() {
      return i`
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

      /* ---- import/export breakdown ---- */
      .breakdown {
        display: flex;
        gap: 12px;
        padding: 8px 12px;
        margin-bottom: 8px;
        background: var(--br-border);
        border-radius: 8px;
        font-size: 12px;
        color: var(--br-text-secondary);
        justify-content: center;
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
    `;
    }
    /* ----- render ---------------------------------------------------- */
    render() {
      const s4 = this._s;
      const bestSizeSt = this._st(s4.best_size);
      const paybackSt = this._st(s4.payback);
      const annualSt = this._st(s4.annual_saving);
      const byCap = bestSizeSt?.attributes?.by_capacity;
      const monthly = bestSizeSt?.attributes?.monthly_data;
      const paybackAttrs = paybackSt?.attributes || {};
      const paybackVal = paybackSt?.state;
      const withinLifetime = paybackAttrs.within_lifetime;
      return b2`
      <ha-card class="card">
        ${this._render_header(bestSizeSt)}
        ${this._render_stats(paybackVal, paybackAttrs, annualSt)}
        ${this._render_secondary_stats(s4)}
        ${byCap ? this._render_chart(byCap) : ""}
        ${monthly ? this._render_heatmap(monthly) : ""}
        ${this._render_lifecycle(paybackAttrs)}
      </ha-card>
    `;
    }
    /* ======================== sub-renderers ========================== */
    _render_header(bestSizeSt) {
      const updated = bestSizeSt?.last_updated ? new Date(bestSizeSt.last_updated).toLocaleString("nl-NL", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit"
      }) : "";
      return b2`
      <div class="header">
        <h2>
          <span>⚡ Battery ROI</span>
          <span class="version">v${CARD_VERSION}</span>
        </h2>
        <span class="updated">${updated}</span>
      </div>
    `;
    }
    _render_stats(paybackVal, paybackAttrs, annualSt) {
      const pb = _num(paybackVal, 1);
      const withinLifetime = paybackAttrs.within_lifetime;
      const pbClass = withinLifetime ? "green" : "red";
      const annual = annualSt?.state ?? "\u2014";
      const upfront = paybackAttrs.upfront_cost_eur;
      const netSaving = Number(paybackAttrs.net_saving_eur);
      const netClass = netSaving >= 0 ? "green" : "red";
      const bestSizeSt = this._st(this._s.best_size);
      const byCap = bestSizeSt?.attributes?.by_capacity || {};
      const bestKey = String(bestSizeSt?.state || "5").replace(".", "_");
      const cap = byCap[bestKey] || {};
      const importSaved = cap.reduced_grid_import_kwh;
      const exportChanged = cap.reduced_export_kwh;
      return b2`
      <div class="grid">
        <div class="stat">
          <div class="value accent">
            ${_num(bestSizeSt?.state, 1)}
          </div>
          <div class="label">Best Size (kWh)</div>
        </div>
        <div class="stat">
          <div class="value ${pbClass}">${pb}</div>
          <div class="label">Payback (yr)</div>
        </div>
        <div class="stat">
          <div class="value green">€${_num(annual, 0)}</div>
          <div class="label">Annual Saving</div>
        </div>
        <div class="stat">
          <div class="value ${netClass}">
            ${_euro(netSaving)}
          </div>
          <div class="label">Net Result (${upfront ? "invest \u20AC" + _num(upfront, 0) + " " : ""}life)</div>
        </div>
      </div>
      ${importSaved != null ? b2`
        <div class="breakdown">
          <span>📥 Import saved: ${_num(importSaved, 0)} kWh/yr</span>
          <span>📤 Export changed: ${_num(exportChanged, 0)} kWh/yr</span>
        </div>
      ` : ""}
    `;
    }
    _render_secondary_stats(s4) {
      return b2`
      <div class="grid">
        <div class="stat">
          <div class="value">${_pct(this._st(s4.self_consumption)?.state)}</div>
          <div class="label">Self-Consumption</div>
        </div>
        <div class="stat">
          <div class="value">${_num(this._st(s4.cycles)?.state, 1)}</div>
          <div class="label">Cycles / Year</div>
        </div>
        <div class="stat">
          <div class="value">${_num(this._st(s4.import_saved)?.state, 0)}</div>
          <div class="label">Import Saved (kWh/yr)</div>
        </div>
        <div class="stat">
          <div class="value">${_num(this._st(s4.export_saved)?.state, 0)}</div>
          <div class="label">Export Saved (kWh/yr)</div>
        </div>
      </div>
    `;
    }
    /* ----- capacity comparison bar chart ----------------------------- */
    _render_chart(byCap) {
      const caps = Object.entries(byCap).map(([k2, v2]) => ({ cap: k2.replace("_", "."), ...v2 })).sort((a3, b3) => Number(a3.cap) - Number(b3.cap));
      const maxPayback = Math.max(
        ...caps.map((c4) => c4.payback_years != null ? c4.payback_years : 0),
        1
      );
      const maxAnnual = Math.max(
        ...caps.map((c4) => c4.annual_saving_eur ?? 0),
        1
      );
      return b2`
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
            ${caps.map(
        (c4) => b2`
                <tr>
                  <td class="cap-label">${c4.cap}</td>
                  <td style="width:35%">
                    <div class="bar-track">
                      <div
                        class="bar-fill annual"
                        style="width:${(c4.annual_saving_eur ?? 0) / maxAnnual * 100}%"
                      ></div>
                    </div>
                  </td>
                  <td class="bar-val">
                    €${_num(c4.annual_saving_eur, 0)}
                  </td>
                  <td style="width:35%">
                    <div class="bar-track">
                      <div
                        class="bar-fill payback ${c4.payback_years != null && c4.payback_years > 20 ? "overshoot" : ""}"
                        style="width:${Math.min(
          (c4.payback_years ?? maxPayback) / maxPayback * 100,
          100
        )}%"
                      ></div>
                    </div>
                  </td>
                  <td class="bar-val">
                    ${c4.payback_years != null ? `${_num(c4.payback_years, 1)} yr` : "\u221E"}
                  </td>
                  <td class="bar-val">
                    ${c4.roi_pct != null ? `${_num(c4.roi_pct, 1)}%` : "\u2014"}
                  </td>
                </tr>
              `
      )}
          </tbody>
        </table>
      </div>
      <div class="chart-legend">
        <span><span class="dot" style="background:var(--br-accent)"></span>Annual Saving</span>
        <span><span class="dot" style="background:var(--br-green)"></span>Payback</span>
      </div>
    `;
    }
    /* ----- monthly heatmap ------------------------------------------- */
    _render_heatmap(monthly) {
      const months = Object.entries(monthly).sort(([a3], [b3]) => a3.localeCompare(b3));
      const maxVal = Math.max(
        ...months.map(([, d3]) => Math.max(d3.battery_out_kwh ?? 0, d3.battery_in_kwh ?? 0)),
        1
      );
      const intensity = (v2) => Math.min(Math.round((v2 ?? 0) / maxVal * 10), 10);
      return b2`
      <div class="section-title">Monthly Battery Usage (kWh)</div>
      <div class="heatmap">
        <span class="hm-label"></span>
        <span class="hm-label" style="text-align:center">In</span>
        <span class="hm-label" style="text-align:center">Out</span>
        ${months.map(
        ([key, d3]) => b2`
            <span class="hm-label">${key}</span>
            <div
              class="hm-cell"
              style="background:var(--br-accent);opacity:${0.1 + intensity(d3.battery_in_kwh) * 0.08}"
              data-tooltip="${key} in: ${_num(d3.battery_in_kwh, 0)} kWh"
            ></div>
            <div
              class="hm-cell"
              style="background:var(--br-green);opacity:${0.1 + intensity(d3.battery_out_kwh) * 0.08}"
              data-tooltip="${key} out: ${_num(d3.battery_out_kwh, 0)} kWh"
            ></div>
          `
      )}
      </div>
      <div class="hm-legend">
        <span class="hm-swatch" style="background:var(--br-accent);opacity:0.8"></span> Charged
        <span class="hm-swatch" style="background:var(--br-green);opacity:0.8"></span> Discharged
        <span style="margin-left:auto">Low ▸ High</span>
      </div>
    `;
    }
    /* ----- lifecycle info -------------------------------------------- */
    _render_lifecycle(attrs) {
      const upfront = attrs.upfront_cost_eur;
      const withinLifetime = attrs.within_lifetime;
      return b2`
      <div class="lifecycle">
        <span>Upfront: ${upfront != null ? _euro(upfront) : "\u2014"}</span>
        <span>Pays back within life: ${_bool(withinLifetime)}</span>
        <span>Annual: €${_num(attrs.annual_saving_eur, 0)}</span>
      </div>
    `;
    }
    /* ----- card metadata (for HA editor) ----------------------------- */
    static async getConfigElement() {
      const el = document.createElement("div");
      el.innerHTML = `
      <style>
        .br-edit { padding: 8px; }
        .br-edit label { display:block; margin:8px 0 4px; font-size:12px; color:var(--secondary-text-color); }
        .br-edit input { width:100%; box-sizing:border-box; }
      </style>
      <div class="br-edit">
        <label>Title (optional)</label>
        <input id="title" placeholder="Battery ROI" />
        <label>Entity prefix (default: sensor.battery_roi)</label>
        <input id="prefix" placeholder="sensor.battery_roi_analyzer" />
      </div>
    `;
      el.querySelector("#title").addEventListener("change", () => {
        el._config = { ...el._config, title: el.querySelector("#title").value || void 0 };
        el.dispatchEvent(new Event("config-changed", { bubbles: true }));
      });
      el.querySelector("#prefix").addEventListener("change", () => {
        el._config = { ...el._config, entity_prefix: el.querySelector("#prefix").value || void 0 };
        el.dispatchEvent(new Event("config-changed", { bubbles: true }));
      });
      el.setConfig = (cfg) => {
        el._config = cfg;
        el.querySelector("#title").value = cfg?.title || "";
        el.querySelector("#prefix").value = cfg?.entity_prefix || "";
      };
      return el;
    }
  };
  customElements.define("battery-roi-card", BatteryRoiCard);
  console.log("[battery-roi] custom element defined");
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "battery-roi-card",
    name: "Battery ROI Analyzer",
    description: "Dashboard card showing battery ROI metrics, capacity comparison, and monthly usage heatmap",
    preview: true,
    documentationURL: "https://github.com/ramonskie/battery-roi-analyzer"
  });
  console.log("[battery-roi] registered in window.customCards");
})();
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
//# sourceMappingURL=battery-roi-card.js.map
