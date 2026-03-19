// plugin_engine.js — Antigravity Data Sync & Auto-Layout Generator

figma.showUI(__html__, { width: 520, height: 650, title: 'Antigravity Data Sync' });

function safeVal(v, d) { return (v !== undefined && v !== null) ? v : d; }

var BLEND_MAP = {
  'NORMAL':'NORMAL','MULTIPLY':'MULTIPLY','SCREEN':'SCREEN','OVERLAY':'OVERLAY','DARKEN':'DARKEN',
  'LIGHTEN':'LIGHTEN','COLOR_DODGE':'COLOR_DODGE','COLOR_BURN':'COLOR_BURN','HARD_LIGHT':'HARD_LIGHT',
  'SOFT_LIGHT':'SOFT_LIGHT','DIFFERENCE':'DIFFERENCE','EXCLUSION':'EXCLUSION','HUE':'HUE',
  'SATURATION':'SATURATION','COLOR':'COLOR','LUMINOSITY':'LUMINOSITY'
};

var importBBox = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };

function updateBBox(x, y, w, h) {
  if (x < importBBox.minX) importBBox.minX = x;
  if (y < importBBox.minY) importBBox.minY = y;
  if ((x + w) > importBBox.maxX) importBBox.maxX = x + w;
  if ((y + h) > importBBox.maxY) importBBox.maxY = y + h;
}

// ── 1. PSD Image Import (텍스트 제외 / 백그라운드 추출용) ──
async function buildGroup(data, parent, pAbsX, pAbsY) {
  var frame = figma.createFrame();
  frame.name = data.name || 'Group';
  frame.resize(Math.max(Math.round(data.width), 1), Math.max(Math.round(data.height), 1));
  
  var rx = Math.round(data.x - pAbsX);
  var ry = Math.round(data.y - pAbsY);
  frame.x = rx; frame.y = ry;
  updateBBox(data.x, data.y, data.width, data.height);

  frame.opacity = safeVal(data.opacity, 1);
  frame.fills = []; frame.clipsContent = false;
  
  parent.appendChild(frame);
  if (!data.children || data.children.length === 0) return;
  for (var i = 0; i < data.children.length; i++) {
    await buildLayer(data.children[i], frame, data.x, data.y);
  }
}

async function buildImage(data, parent, pAbsX, pAbsY) {
  var rect = figma.createRectangle();
  rect.name = data.name || 'Image';
  rect.resize(Math.max(Math.round(data.width), 1), Math.max(Math.round(data.height), 1));
  if (data.imageBytes) {
    try {
      var img = figma.createImage(new Uint8Array(data.imageBytes));
      rect.fills = [{ type:'IMAGE', imageHash:img.hash, scaleMode:'FILL' }];
    } catch(e){ rect.fills = [{ type:'SOLID', color:{r:0.9, g:0.9, b:0.9} }]; }
  }
  parent.appendChild(rect);
  rect.x = Math.round(data.x - pAbsX);
  rect.y = Math.round(data.y - pAbsY);
  updateBBox(data.x, data.y, data.width, data.height);
}

async function buildLayer(data, parent, pAbsX, pAbsY) {
  if (data.type === 'group') return buildGroup(data, parent, pAbsX, pAbsY);
  // 텍스트는 임포트 로직에서 완전 제외 (사용자가 직접 피그마에서 오토 레이아웃으로 텍스트를 작성하도록 유도)
  if (data.type === 'image') return buildImage(data, parent, pAbsX, pAbsY);
}

figma.ui.onmessage = async function(msg) {

  // ================= PSD 배경 추출 =================
  if (msg.type === 'import-psd-bg') {
    try {
      var layers = msg.layers;
      var root = figma.createFrame();
      root.name = 'PSD 배경 소스 (여기에 텍스트를 올리세요)';
      
      importBBox = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
      for (var i = 0; i < layers.length; i++) { await buildLayer(layers[i], root, 0, 0); }
      
      if (importBBox.minX < Infinity) {
        var w = Math.max(Math.round(importBBox.maxX - importBBox.minX), 1);
        var h = Math.max(Math.round(importBBox.maxY - importBBox.minY), 1);
        root.resizeWithoutConstraints(w, h);
        for (var j = 0; j < root.children.length; j++) {
          root.children[j].x -= importBBox.minX; root.children[j].y -= importBBox.minY;
        }
      }
      root.x = figma.viewport.center.x - root.width / 2;
      root.y = figma.viewport.center.y - root.height / 2;
      
      figma.currentPage.selection = [root];
      figma.viewport.scrollAndZoomIntoView([root]);
      figma.ui.postMessage({ type: 'done', message: '배경 소스가 깨끗하게 추출되었습니다! 이 위에 피그마 텍스트 툴로 직접 글자를 입력해 템플릿을 완성하세요.' });
    } catch (err) { figma.ui.postMessage({ type: 'error', message: err.message }); }
  }

  // ================= 기본 오토레이아웃 템플릿 생성 =================
  if (msg.type === 'create-basic-template') {
    try {
      await figma.loadFontAsync({ family: "Inter", style: "Medium" });
      await figma.loadFontAsync({ family: "Inter", style: "Bold" });
      await figma.loadFontAsync({ family: "Inter", style: "Regular" });
      
      var frame = figma.createFrame();
      frame.name = "기본 가격표 템플릿";
      frame.resize(400, 400);
      frame.fills = [{ type: 'SOLID', color: { r: 1, g: 0.9, b: 0.95 } }]; // 연한 핑크 배경
      frame.cornerRadius = 24;
      
      // 제목 그룹
      var titleGroup = figma.createFrame();
      titleGroup.name = "타이틀 영역";
      titleGroup.layoutMode = "VERTICAL";
      titleGroup.primaryAxisAlignItems = "CENTER";
      titleGroup.counterAxisAlignItems = "CENTER";
      titleGroup.itemSpacing = 8;
      titleGroup.fills = [];
      titleGroup.layoutSizingHorizontal = "HUG";
      titleGroup.layoutSizingVertical = "HUG";
      
      var title1 = figma.createText();
      title1.fontName = { family: "Inter", style: "Bold" };
      title1.characters = "봄날 세일";
      title1.fontSize = 28;
      title1.name = "타이틀1";
      
      var title2 = figma.createText();
      title2.fontName = { family: "Inter", style: "Medium" };
      title2.characters = "바로그 구미점 4월 이벤트";
      title2.fontSize = 16;
      title2.name = "타이틀2";
      title2.fills = [{ type: 'SOLID', color: { r: 0.9, g: 0.3, b: 0.4 } }];
      
      titleGroup.appendChild(title1);
      titleGroup.appendChild(title2);
      
      // 가격 박스 (Auto Layout)
      var priceBox = figma.createFrame();
      priceBox.name = "가격 박스";
      priceBox.layoutMode = "VERTICAL";
      priceBox.fills = [{ type: 'SOLID', color: { r: 1, g: 1, b: 1 } }];
      priceBox.cornerRadius = 12;
      priceBox.paddingLeft = 24; priceBox.paddingRight = 24;
      priceBox.paddingTop = 24; priceBox.paddingBottom = 24;
      priceBox.itemSpacing = 16;
      priceBox.layoutSizingHorizontal = "FIXED";
      priceBox.resize(340, 200); // fixed width
      
      var HeaderBox = figma.createFrame();
      HeaderBox.layoutMode = "HORIZONTAL";
      HeaderBox.primaryAxisAlignItems = "CENTER";
      HeaderBox.counterAxisAlignItems = "CENTER";
      HeaderBox.fills = [{ type: 'SOLID', color: { r: 0.9, g: 0.3, b: 0.4 } }];
      HeaderBox.cornerRadius = 8;
      HeaderBox.layoutSizingHorizontal = "FILL";
      HeaderBox.paddingTop = 8; HeaderBox.paddingBottom = 8;
      
      var headerText = figma.createText();
      headerText.fontName = { family: "Inter", style: "Bold" };
      headerText.characters = "피부 이벤트";
      headerText.fontSize = 18;
      headerText.fills = [{ type: 'SOLID', color: { r: 1, g: 1, b: 1 } }];
      headerText.name = "카테고리명";
      HeaderBox.appendChild(headerText);
      priceBox.appendChild(HeaderBox);
      
      var itemRow = figma.createFrame();
      itemRow.layoutMode = "HORIZONTAL";
      itemRow.primaryAxisAlignItems = "SPACE_BETWEEN";
      itemRow.counterAxisAlignItems = "CENTER";
      itemRow.fills = [];
      itemRow.layoutSizingHorizontal = "FILL";
      
      var itemName = figma.createText();
      itemName.fontName = { family: "Inter", style: "Medium" };
      itemName.characters = "포텐자(펌핑팁)+스킨부스터";
      itemName.fontSize = 14;
      itemName.name = "상품명";
      itemName.layoutSizingHorizontal = "FILL"; // 영역 꽉 채우기
      
      var priceWrap = figma.createFrame();
      priceWrap.layoutMode = "HORIZONTAL";
      priceWrap.counterAxisAlignItems = "BASELINE";
      priceWrap.itemSpacing = 4;
      priceWrap.fills = [];
      
      var priceNum = figma.createText();
      priceNum.fontName = { family: "Inter", style: "Bold" };
      priceNum.characters = "30";
      priceNum.fontSize = 24;
      priceNum.fills = [{ type: 'SOLID', color: { r: 0.9, g: 0.3, b: 0.4 } }];
      priceNum.name = "가격(숫자)";
      
      var priceUnit = figma.createText();
      priceUnit.fontName = { family: "Inter", style: "Regular" };
      priceUnit.characters = "만";
      priceUnit.fontSize = 14;
      priceUnit.name = "단위";
      
      priceWrap.appendChild(priceNum);
      priceWrap.appendChild(priceUnit);
      
      itemRow.appendChild(itemName);
      itemRow.appendChild(priceWrap);
      priceBox.appendChild(itemRow);
      
      // 부모 프레임에 오토 레이아웃 적용
      frame.layoutMode = "VERTICAL";
      frame.primaryAxisAlignItems = "CENTER";
      frame.counterAxisAlignItems = "CENTER";
      frame.itemSpacing = 24;
      frame.appendChild(titleGroup);
      frame.appendChild(priceBox);
      
      frame.x = figma.viewport.center.x - frame.width / 2;
      frame.y = figma.viewport.center.y - frame.height / 2;
      
      figma.currentPage.selection = [frame];
      figma.viewport.scrollAndZoomIntoView([frame]);
      figma.ui.postMessage({ type: 'done', message: '오토 레이아웃이 적용된 완벽한 기본 템플릿이 생성되었습니다! 레이어명을 확인하고 데이터 영역에 복붙해보세요.' });
    } catch(e) { figma.ui.postMessage({ type: 'error', message: e.message }); }
  }

  // ================= 시트 데이터 기반 대량 복제 (Data Sync) =================
  if (msg.type === 'generate-variants') {
    var sel = figma.currentPage.selection;
    if (sel.length !== 1 || sel[0].type !== 'FRAME') {
      return figma.ui.postMessage({ type: 'error', message: '먼저 템플릿으로 사용할 프레임 1개를 선택해주세요.' });
    }
    
    var template = sel[0];
    var dataRows = msg.data;
    
    var textNodes = template.findAll(function(n) { return n.type === 'TEXT'; });
    var fontsToLoad = [];
    textNodes.forEach(function(node) {
      var f = node.fontName;
      if (f && f !== figma.mixed) {
        if (!fontsToLoad.some(function(lf) { return lf.family === f.family && lf.style === f.style; })) {
          fontsToLoad.push(f);
        }
      }
    });
    
    for (var k = 0; k < fontsToLoad.length; k++) {
      try { await figma.loadFontAsync(fontsToLoad[k]); } catch(e) {}
    }
    
    var startX = template.x + template.width + 100;
    var startY = template.y;
    var cols = 5;
    var generated = [];
    
    for (var r = 0; r < dataRows.length; r++) {
      var rowData = dataRows[r];
      var clone = template.clone();
      clone.name = template.name + " - Variant " + (r + 1);
      
      clone.x = startX + (r % cols) * (template.width + 50);
      clone.y = startY + Math.floor(r / cols) * (template.height + 50);
      
      var cloneTexts = clone.findAll(function(n) { return n.type === 'TEXT'; });
      for (var j = 0; j < cloneTexts.length; j++) {
        var n = cloneTexts[j];
        if (rowData[n.name] !== undefined) {
          n.characters = rowData[n.name].toString();
        }
      }
      generated.push(clone);
    }
    
    figma.currentPage.selection = generated;
    figma.viewport.scrollAndZoomIntoView(generated);
    figma.ui.postMessage({ type: 'done', message: dataRows.length + '개의 디자인이 완벽하게 생성되었습니다!' });
  }

  if (msg.type === 'close') figma.closePlugin();
};