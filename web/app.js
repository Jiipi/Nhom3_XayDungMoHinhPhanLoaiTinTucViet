/**
 * VietNews AI — Client Application Logic
 */

// Category icons & color mappings
const CATEGORY_MAP = {
  "cong-nghe": { name: "Công nghệ", icon: "fa-microchip", color: "#06b6d4" },
  "kinh-doanh": { name: "Kinh doanh", icon: "fa-chart-line", color: "#10b981" },
  "the-thao": { name: "Thể thao", icon: "fa-futbol", color: "#f59e0b" },
  "thoi-su": { name: "Thời sự", icon: "fa-newspaper", color: "#3b82f6" },
  "giai-tri": { name: "Giải trí", icon: "fa-masks-theater", color: "#ec4899" },
  "suc-khoe": { name: "Sức khỏe", icon: "fa-heart-pulse", color: "#ef4444" },
  "giao-duc": { name: "Giáo dục", icon: "fa-graduation-cap", color: "#8b5cf6" },
  "phap-luat": { name: "Pháp luật", icon: "fa-scale-balanced", color: "#6366f1" },
  "du-lich": { name: "Du lịch", icon: "fa-plane-departure", color: "#14b8a6" },
  "doi-song": { name: "Đời sống", icon: "fa-house-user", color: "#84cc16" },
  "xe": { name: "Xe / Ô tô", icon: "fa-car", color: "#f97316" }
};

// Curated sample articles for instant testing
const SAMPLE_ARTICLES = [
  {
    id: "sample-tech",
    pill: "💻 Công nghệ",
    category: "cong-nghe",
    title: "AI Trung Quốc thua đậm đại diện Mỹ ở giải cờ vua AI đầu tiên",
    content: "Hai Mô hình Ngôn ngữ Lớn (LLMs) của Trung Quốc là DeepSeek và Kimi K2 đều thua 0-4 trước đại diện OpenAI (Mỹ) tại tứ kết giải cờ vua AI do Google tổ chức. Mô hình o3 của OpenAI thắng áp đảo khi AI đối phương liên tục đưa ra các nước đi không hợp lệ theo luật cờ vua quốc tế."
  },
  {
    id: "sample-biz",
    pill: "📈 Kinh doanh",
    category: "kinh-doanh",
    title: "Giá vàng nhẫn tăng kỷ lục lên mốc 89 triệu đồng/lượng",
    content: "Giá vàng nhẫn trong nước tiếp tục đà tăng mạnh theo giá vàng thế giới. Doanh nghiệp kinh doanh vàng lớn niêm yết giá bán ra áp sát mốc 89 triệu đồng mỗi lượng trong bối cảnh nhà đầu tư gia tăng mua tích trữ và lo ngại lạm phát toàn cầu."
  },
  {
    id: "sample-sports",
    pill: "⚽ Thể thao",
    category: "the-thao",
    title: "Cơ thủ Dương Quốc Hoàng giúp đội châu Á dẫn trước tại Reyes Cup",
    content: "Cơ thủ billiard Dương Quốc Hoàng cùng đồng đội Johann Chua xuất sắc đánh bại cặp đôi đối thủ mạnh từ đội Thế giới với tỷ số 5-4, giúp đội châu Á vươn lên dẫn trước 4-0 sau ngày thi đấu đầu tiên tại Reyes Cup 2025 ở Manila."
  },
  {
    id: "sample-edu",
    pill: "🎓 Giáo dục",
    category: "giao-duc",
    title: "8 trường đại học công bố công cụ tự động quy đổi điểm xét tuyển",
    content: "Đại học Bách khoa Hà Nội, Đại học Kinh tế Quốc dân cùng 6 trường đại học lớn khác đã xây dựng phần mềm tự động quy đổi điểm giữa các phương thức xét tuyển như thi Đánh giá năng lực HSA, APT, tư duy TSA và điểm tốt nghiệp THPT."
  },
  {
    id: "sample-health",
    pill: "🏥 Sức khỏe",
    category: "suc-khoe",
    title: "Bộ Y tế cảnh báo thời điểm gia tăng các bệnh đường hô hấp mùa lạnh",
    content: "Thời tiết chuyển mùa lạnh khiến số ca mắc cúm A, viêm phổi và các bệnh đường hô hấp gia tăng tại nhiều tỉnh phía Bắc. Các bác sĩ khuyến cáo người dân, đặc biệt là người già và trẻ em, nên chủ động tiêm vắc xin phòng bệnh."
  }
];

// DOM Elements Initialization
document.addEventListener("DOMContentLoaded", () => {
  initSamplePills();
  initFormEvents();
  checkApiHealth();
});

// Render Sample Article Pills
function initSamplePills() {
  const container = document.getElementById("samplePills");
  if (!container) return;

  container.innerHTML = SAMPLE_ARTICLES.map(art => `
    <button class="sample-pill" data-id="${art.id}">
      ${art.pill}
    </button>
  `).join("");

  container.addEventListener("click", (e) => {
    const pillBtn = e.target.closest(".sample-pill");
    if (!pillBtn) return;

    const sampleId = pillBtn.dataset.id;
    const sample = SAMPLE_ARTICLES.find(s => s.id === sampleId);
    if (!sample) return;

    // Set active class
    document.querySelectorAll(".sample-pill").forEach(btn => btn.classList.remove("active"));
    pillBtn.classList.add("active");

    // Populate inputs
    document.getElementById("newsTitle").value = sample.title;
    document.getElementById("newsContent").value = sample.content;
    updateCharCounter();

    // Trigger classification immediately for great UX
    classifyText(sample.title, sample.content);
  });
}

// Form Events & Character Counter
function initFormEvents() {
  const contentInput = document.getElementById("newsContent");
  const titleInput = document.getElementById("newsTitle");
  const btnClear = document.getElementById("btnClear");
  const form = document.getElementById("classifyForm");

  contentInput.addEventListener("input", updateCharCounter);
  titleInput.addEventListener("input", updateCharCounter);

  btnClear.addEventListener("click", () => {
    titleInput.value = "";
    contentInput.value = "";
    updateCharCounter();
    document.querySelectorAll(".sample-pill").forEach(btn => btn.classList.remove("active"));
    resetResultPanel();
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const title = titleInput.value.trim();
    const content = contentInput.value.trim();

    if (!content) {
      alert("Vui lòng nhập nội dung bài báo!");
      return;
    }

    classifyText(title, content);
  });
}

function updateCharCounter() {
  const content = document.getElementById("newsContent").value.trim();
  const wordCount = content ? content.split(/\s+/).length : 0;
  document.getElementById("charCounter").innerText = `${wordCount} từ`;
}

// API Connection & Classification Logic
async function classifyText(title, content) {
  setLoadingState(true);
  const startTime = performance.now();

  try {
    const response = await fetch("/api/classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content })
    });

    let data;
    if (response.ok) {
      data = await response.json();
    } else {
      // Fallback local heuristic predictor if backend is static/mock server
      data = fallbackLocalPredictor(title, content);
    }

    const elapsed = Math.round(performance.now() - startTime);
    document.getElementById("inferenceTime").innerText = `~${elapsed}ms`;

    renderResults(data);
  } catch (err) {
    console.warn("API request failed, using client-side prediction engine fallback...", err);
    const fallbackData = fallbackLocalPredictor(title, content);
    const elapsed = Math.round(performance.now() - startTime);
    document.getElementById("inferenceTime").innerText = `~${elapsed}ms`;
    renderResults(fallbackData);
  } finally {
    setLoadingState(false);
  }
}

// Render Results with Smooth Animations
function renderResults(data) {
  const placeholder = document.getElementById("placeholderState");
  const resultContent = document.getElementById("resultContent");

  placeholder.classList.add("hidden");
  resultContent.classList.remove("hidden");

  // Top Result Card
  const primaryCatKey = data.primary_category;
  const catMeta = CATEGORY_MAP[primaryCatKey] || { name: data.primary_name || primaryCatKey, icon: "fa-layer-group", color: "#3b82f6" };

  document.getElementById("predIcon").innerHTML = `<i class="fa-solid ${catMeta.icon}"></i>`;
  document.getElementById("predTitle").innerText = catMeta.name;
  
  const confidencePercent = (data.confidence * 100).toFixed(1);
  animateConfidenceCounter("predConfidenceVal", parseFloat(confidencePercent));

  // Keywords Highlight
  const keywordsContainer = document.getElementById("keywordsList");
  if (data.keywords && data.keywords.length > 0) {
    keywordsContainer.innerHTML = data.keywords.map(kw => `<span class="key-tag">${kw}</span>`).join("");
  } else {
    keywordsContainer.innerHTML = `<span class="key-tag">nội dung báo chí</span><span class="key-tag">từ khóa tổng hợp</span>`;
  }

  // Distribution Bars (11 Categories)
  const barsContainer = document.getElementById("barsContainer");
  const sortedDist = data.distribution.sort((a, b) => b.score - a.score);

  barsContainer.innerHTML = sortedDist.map((item, index) => {
    const catInfo = CATEGORY_MAP[item.category] || { name: item.name || item.category };
    const pct = (item.score * 100).toFixed(1);
    const isTop = index === 0;

    return `
      <div class="cat-bar-item">
        <div class="cat-bar-meta">
          <span class="cat-bar-name">${catInfo.name}</span>
          <span class="cat-bar-score">${pct}%</span>
        </div>
        <div class="cat-bar-track">
          <div class="cat-bar-fill ${isTop ? 'top-fill' : ''}" data-target="${pct}" style="width: 0%"></div>
        </div>
      </div>
    `;
  }).join("");

  // Animate Bar Fills
  setTimeout(() => {
    document.querySelectorAll(".cat-bar-fill").forEach(bar => {
      const targetWidth = bar.getAttribute("data-target");
      bar.style.width = `${targetWidth}%`;
    });
  }, 50);
}

// Animated Confidence Counter
function animateConfidenceCounter(elementId, targetValue) {
  const el = document.getElementById(elementId);
  let current = 0;
  const duration = 600; // ms
  const stepTime = 20;
  const steps = duration / stepTime;
  const increment = targetValue / steps;

  const timer = setInterval(() => {
    current += increment;
    if (current >= targetValue) {
      current = targetValue;
      clearInterval(timer);
    }
    el.innerText = `${current.toFixed(1)}%`;
  }, stepTime);
}

function resetResultPanel() {
  document.getElementById("placeholderState").classList.remove("hidden");
  document.getElementById("resultContent").classList.add("hidden");
}

function setLoadingState(isLoading) {
  const btn = document.getElementById("btnClassify");
  const btnText = btn.querySelector(".btn-text");
  const btnSpinner = btn.querySelector(".btn-spinner");

  if (isLoading) {
    btn.disabled = true;
    btnText.classList.add("hidden");
    btnSpinner.classList.remove("hidden");
  } else {
    btn.disabled = false;
    btnText.classList.remove("hidden");
    btnSpinner.classList.add("hidden");
  }
}

// Client-side Fallback Heuristic Classifier (Ensures standalone preview works effortlessly)
function fallbackLocalPredictor(title, content) {
  const text = (title + " " + content).toLowerCase();
  
  const scores = {
    "cong-nghe": 0.05,
    "kinh-doanh": 0.05,
    "the-thao": 0.05,
    "thoi-su": 0.05,
    "giai-tri": 0.05,
    "suc-khoe": 0.05,
    "giao-duc": 0.05,
    "phap-luat": 0.05,
    "du-lich": 0.05,
    "doi-song": 0.05,
    "xe": 0.05
  };

  const kwRules = {
    "cong-nghe": ["ai", "trí tuệ nhân tạo", "công nghệ", "phần mềm", "app", "llm", "chatgpt", "openai", "deepseek", "robot", "chip", "iphone"],
    "kinh-doanh": ["giá vàng", "doanh nghiệp", "lợi nhuận", "kinh tế", "chứng khoán", "tài chính", "ngân hàng", "lạm phát", "đầu tư", "lượng"],
    "the-thao": ["cơ thủ", "bóng đá", "giải đấu", "tỷ số", "đồng đội", "vô địch", "billiards", "ryder cup", "huy chương", "trận đấu"],
    "giao-duc": ["đại học", "xét tuyển", "thí sinh", "điểm chuẩn", "bách khoa", "thpt", "trường", "học phí", "giáo dục"],
    "suc-khoe": ["bệnh", "y tế", "bác sĩ", "vắc xin", "hô hấp", "cúm", "sức khỏe", "bệnh viện", "dịch bệnh"],
    "giai-tri": ["phim", "diễn viên", "ca sĩ", "nghệ sĩ", "show", "giải trí", "hollywood", "album", "nhạc"],
    "phap-luat": ["công an", "điều tra", "vụ án", "xử phạt", "tòa án", "pháp luật", "tội phạm", "bắt giữ"],
    "du-lich": ["du lịch", "khách sạn", "điểm đến", "vé máy bay", "tour", "nghỉ dưỡng", "bãi biển"],
    "xe": ["ô tô", "xe máy", "xe điện", "động cơ", "vinfast", "hyundai", "toyota", "lái xe"]
  };

  const detectedKws = [];
  for (const [cat, kws] of Object.entries(kwRules)) {
    for (const kw of kws) {
      if (text.includes(kw)) {
        scores[cat] += 0.35;
        if (!detectedKws.includes(kw) && detectedKws.length < 5) {
          detectedKws.push(kw);
        }
      }
    }
  }

  // Normalize scores to sum = 1.0
  const totalScore = Object.values(scores).reduce((a, b) => a + b, 0);
  const distribution = Object.entries(scores).map(([cat, raw]) => ({
    category: cat,
    name: CATEGORY_MAP[cat] ? CATEGORY_MAP[cat].name : cat,
    score: parseFloat((raw / totalScore).toFixed(4))
  })).sort((a, b) => b.score - a.score);

  return {
    primary_category: distribution[0].category,
    primary_name: distribution[0].name,
    confidence: distribution[0].score,
    keywords: detectedKws.length > 0 ? detectedKws : ["tin tức", "tổng hợp"],
    distribution: distribution
  };
}

async function checkApiHealth() {
  try {
    const res = await fetch("/api/stats");
    if (res.ok) {
      document.getElementById("statusText").innerText = "PhoBERT Engine — Live (Connected)";
    }
  } catch (e) {
    document.getElementById("statusText").innerText = "PhoBERT Engine — Standalone Mode";
  }
}
