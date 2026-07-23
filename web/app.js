/**
 * VietNews AI V4 — Client Application Logic
 */

// Category icons & color mappings for 11 standard topics
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

// Curated sample articles covering major topics
const SAMPLE_ARTICLES = [
  {
    id: "sample-car",
    pill: "🚗 Xe / Ô tô",
    category: "xe",
    title: "Cửa lên xuống xe khách và những yếu tố an toàn cơ bản",
    content: "Yếu tố an toàn của mỗi chiếc xe khách không đơn thuần chỉ nằm ở số lượng cửa lên xuống xe. Xe khách chỉ có một cửa lên xuống vẫn đảm bảo an toàn nếu được thiết kế đúng tiêu chuẩn và trang bị đầy đủ các phương án thoát hiểm. Quan trọng là trước khi bắt đầu chuyến đi, chủ xe, tài xế cần kiểm tra hệ thống cửa thoát hiểm, trang bị búa phá kính và đặc biệt nên có những chỉ dẫn an toàn cơ bản cho hành khách."
  },
  {
    id: "sample-tech",
    pill: "💻 Công nghệ",
    category: "cong-nghe",
    title: "AI Trung Quốc thua đại diện Mỹ ở giải cờ vua AI",
    content: "Hai Mô hình Ngôn ngữ Lớn (LLMs) của Trung Quốc là DeepSeek và Kimi K2 đều thua trước đại diện OpenAI (Mỹ) tại tứ kết giải cờ vua AI do Google tổ chức. Mô hình o3 của OpenAI thắng áp đảo khi phần mềm đối phương liên tục đưa ra các nước đi không hợp lệ."
  },
  {
    id: "sample-biz",
    pill: "📈 Kinh doanh",
    category: "kinh-doanh",
    title: "Giá vàng nhẫn tăng kỷ lục lên mốc 89 triệu đồng/lượng",
    content: "Giá vàng nhẫn trong nước tiếp tục đà tăng mạnh theo giá vàng thế giới. Doanh nghiệp kinh doanh vàng lớn niêm yết giá bán ra áp sát mốc 89 triệu đồng mỗi lượng trong bối cảnh thị trường tài chính chứng khoản và ngân hàng gia tăng giao dịch."
  },
  {
    id: "sample-sports",
    pill: "⚽ Thể thao",
    category: "the-thao",
    title: "Cơ thủ Dương Quốc Hoàng giúp đội châu Á dẫn trước tại Reyes Cup",
    content: "Cơ thủ billiard Dương Quốc Hoàng cùng đồng đội Johann Chua xuất sắc đánh bại cặp đôi đối thủ mạnh từ đội Thế giới với tỷ số 5-4, giúp đội châu Á vươn lên dẫn trước 4-0 sau ngày thi đấu đầu tiên bóng đá và thể thao khu vực."
  },
  {
    id: "sample-edu",
    pill: "🎓 Giáo dục",
    category: "giao-duc",
    title: "8 trường đại học công bố công cụ tự động quy đổi điểm xét tuyển",
    content: "Đại học Bách khoa Hà Nội, Đại học Kinh tế Quốc dân cùng 6 trường đại học lớn khác đã xây dựng công cụ quy đổi điểm cho học sinh lớp 12 giữa các phương thức xét tuyển như thi Đánh giá năng lực HSA, TSA và điểm thi tốt nghiệp THPT."
  },
  {
    id: "sample-health",
    pill: "🏥 Sức khỏe",
    category: "suc-khoe",
    title: "Bộ Y tế cảnh báo gia tăng các bệnh đường hô hấp mùa lạnh",
    content: "Thời tiết chuyển mùa lạnh khiến số ca mắc cúm A, viêm phổi và các bệnh đường hô hấp gia tăng tại nhiều bệnh viện. Các bác sĩ khuyến cáo người dân, đặc biệt là người già và trẻ em, nên chủ động tiêm vắc xin phòng bệnh."
  },
  {
    id: "sample-law",
    pill: "⚖️ Pháp luật",
    category: "phap-luat",
    title: "Công an khởi tố vụ án lừa đảo tài sản trên không gian mạng",
    content: "Cơ quan cảnh sát điều tra công an tỉnh vừa ra quyết định khởi tố vụ án hình sự, bắt tạm giam 3 bị can về hành vi lừa đảo chiếm đoạt tài sản. Qua quá trình thanh tra và điều tra tòa án, cơ quan công an phát hiện nhóm đối tượng giả danh ngân hàng."
  },
  {
    id: "sample-ent",
    pill: "🎬 Giải trí",
    category: "giai-tri",
    title: "Dàn diễn viên và ca sĩ xuất hiện rực rỡ tại lễ công chiếu phim",
    content: "Buổi ra mắt bộ phim điện ảnh bom tấn thu hút sự tham gia của đông đảo nghệ sĩ, ca sĩ và diễn viên nổi tiếng trong giới showbiz. Tác phẩm hứa hẹn mang lại làn gió mới cho rạp chiếu phim Việt Nam trong mùa lễ năm nay."
  },
  {
    id: "sample-travel",
    pill: "✈️ Du lịch",
    category: "du-lich",
    title: "Vé máy bay và khách sạn tại các điểm đến du lịch cháy hàng",
    content: "Lượng khách du lịch đặt tour nghỉ dưỡng ven biển tăng đột biến trong kỳ nghỉ tới. Các khu resort khách sạn 5 sao tại Phú Quốc, Đà Nẵng và Nha Trang đều ghi nhận tỷ lệ lấp đầy phòng đạt trên 95%."
  }
];

let lastResultData = null;

// DOM Ready Event Listener
document.addEventListener("DOMContentLoaded", () => {
  initSamplePills();
  initFormEvents();
  initModalEvents();
  checkApiHealth();
});

// Render Quick Sample Pills
function initSamplePills() {
  const container = document.getElementById("samplePills");
  if (!container) return;

  container.innerHTML = SAMPLE_ARTICLES.map(art => `
    <button type="button" class="sample-pill" data-id="${art.id}">
      ${art.pill}
    </button>
  `).join("");

  container.addEventListener("click", (e) => {
    const pillBtn = e.target.closest(".sample-pill");
    if (!pillBtn) return;

    const sampleId = pillBtn.dataset.id;
    const sample = SAMPLE_ARTICLES.find(s => s.id === sampleId);
    if (!sample) return;

    // Active pill state
    document.querySelectorAll(".sample-pill").forEach(btn => btn.classList.remove("active"));
    pillBtn.classList.add("active");

    // Fill form
    document.getElementById("newsTitle").value = sample.title;
    document.getElementById("newsContent").value = sample.content;
    updateTextStats();

    // Instant trigger classification
    classifyText(sample.title, sample.content);
  });
}

// Form Controls & Input Events
function initFormEvents() {
  const form = document.getElementById("classifyForm");
  const contentInput = document.getElementById("newsContent");
  const titleInput = document.getElementById("newsTitle");
  const btnClear = document.getElementById("btnClear");
  const btnCopy = document.getElementById("btnCopyResult");

  if (contentInput) {
    contentInput.addEventListener("input", updateTextStats);
  }

  if (btnClear) {
    btnClear.addEventListener("click", () => {
      titleInput.value = "";
      contentInput.value = "";
      updateTextStats();
      document.querySelectorAll(".sample-pill").forEach(btn => btn.classList.remove("active"));
      resetResultPanel();
      showToast("Đã xóa nội dung bài viết");
    });
  }

  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const title = titleInput.value.trim();
      const content = contentInput.value.trim();
      if (!content) {
        showToast("Vui lòng nhập nội dung bài báo!", "error");
        return;
      }
      classifyText(title, content);
    });
  }

  if (btnCopy) {
    btnCopy.addEventListener("click", copyAnalysisResult);
  }
}

// Update Word Count & Reading Time
function updateTextStats() {
  const content = document.getElementById("newsContent").value.trim();
  const words = content ? content.split(/\s+/).filter(Boolean).length : 0;
  
  const charCounter = document.getElementById("charCounter");
  const readTime = document.getElementById("readTime");

  if (charCounter) charCounter.innerText = `${words.toLocaleString()} từ`;
  if (readTime) {
    const minutes = Math.max(1, Math.ceil(words / 200));
    readTime.innerText = words > 0 ? `~${minutes} phút đọc` : `0 phút đọc`;
  }
}

// Reset Result Panel to Placeholder
function resetResultPanel() {
  document.getElementById("placeholderState").classList.remove("hidden");
  document.getElementById("loadingState").classList.add("hidden");
  document.getElementById("resultContent").classList.add("hidden");
}

// Call API & Handle Predictions
async function classifyText(title, content) {
  const btnClassify = document.getElementById("btnClassify");
  const btnText = btnClassify.querySelector(".btn-text");
  const btnSpinner = btnClassify.querySelector(".btn-spinner");

  // Show Loading States
  btnClassify.disabled = true;
  if (btnText) btnText.classList.add("hidden");
  if (btnSpinner) btnSpinner.classList.remove("hidden");

  document.getElementById("placeholderState").classList.add("hidden");
  document.getElementById("resultContent").classList.add("hidden");
  document.getElementById("loadingState").classList.remove("hidden");

  const startTime = performance.now();

  try {
    const response = await fetch("/api/classify", {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ title, content })
    });

    if (!response.ok) throw new Error("HTTP error " + response.status);

    const data = await response.json();
    const elapsed = Math.round(performance.now() - startTime);
    
    // Update Inference speed counter
    const infSpeed = document.getElementById("inferenceTime");
    if (infSpeed) infSpeed.innerText = `~${elapsed}ms`;

    lastResultData = { title, content, data };

    renderResults(data);

  } catch (err) {
    console.error("API error:", err);
    showToast("Không thể kết nối đến máy chủ API phân loại", "error");
    resetResultPanel();
  } finally {
    btnClassify.disabled = false;
    if (btnText) btnText.classList.remove("hidden");
    if (btnSpinner) btnSpinner.classList.add("hidden");
    document.getElementById("loadingState").classList.add("hidden");
  }
}

// Render Prediction Results & Animated Visuals
function renderResults(data) {
  const resultContent = document.getElementById("resultContent");
  if (!resultContent) return;

  resultContent.classList.remove("hidden");

  // Top Result Data
  const topCatKey = data.primary_category;
  const catConfig = CATEGORY_MAP[topCatKey] || { name: data.primary_name, icon: "fa-folder", color: "#06b6d4" };
  const confidencePct = (data.confidence * 100).toFixed(1);

  // 1. Update Primary Header & Icon
  const predIcon = document.getElementById("predIcon");
  const predTitle = document.getElementById("predTitle");
  const predConfidenceVal = document.getElementById("predConfidenceVal");
  const gaugeProgress = document.getElementById("gaugeProgress");

  if (predIcon) {
    predIcon.innerHTML = `<i class="fa-solid ${catConfig.icon}"></i>`;
    predIcon.style.color = catConfig.color;
    predIcon.style.backgroundColor = `${catConfig.color}20`;
    predIcon.style.boxShadow = `0 0 20px ${catConfig.color}40`;
  }

  if (predTitle) {
    predTitle.innerText = catConfig.name;
  }

  if (predConfidenceVal) {
    predConfidenceVal.innerText = `${confidencePct}%`;
  }

  // Animate SVG Gauge Circle (Radius 42 -> circumference ~264)
  if (gaugeProgress) {
    gaugeProgress.style.stroke = catConfig.color;
    const offset = 264 - (264 * (data.confidence || 0));
    setTimeout(() => {
      gaugeProgress.style.strokeDashoffset = offset;
    }, 50);
  }

  // 2. Keywords Chips
  const keywordsList = document.getElementById("keywordsList");
  const keywordsBox = document.getElementById("keywordsBox");
  if (keywordsList) {
    if (data.keywords && data.keywords.length > 0) {
      keywordsBox.classList.remove("hidden");
      keywordsList.innerHTML = data.keywords.map((kw, idx) => `
        <span class="keyword-chip" style="animation-delay: ${idx * 0.08}s">
          #${kw}
        </span>
      `).join("");
    } else {
      keywordsBox.classList.add("hidden");
    }
  }

  // 3. Render 11 Categories Ranking Distribution Bars
  const barsContainer = document.getElementById("barsContainer");
  if (barsContainer && data.distribution) {
    barsContainer.innerHTML = data.distribution.map((item, idx) => {
      const cfg = CATEGORY_MAP[item.category] || { name: item.name, icon: "fa-folder", color: "#3b82f6" };
      const scorePct = (item.score * 100).toFixed(1);
      const rankClass = idx === 0 ? "rank-1" : idx === 1 ? "rank-2" : idx === 2 ? "rank-3" : "";

      return `
        <div class="bar-row">
          <div class="bar-meta">
            <div class="bar-cat-info">
              <span class="rank-tag ${rankClass}">${idx + 1}</span>
              <i class="fa-solid ${cfg.icon}" style="color: ${cfg.color}; font-size: 13px;"></i>
              <span class="bar-name">${cfg.name}</span>
            </div>
            <span class="bar-score">${scorePct}%</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill" id="barFill_${idx}" style="background: linear-gradient(90deg, ${cfg.color}80, ${cfg.color});"></div>
          </div>
        </div>
      `;
    }).join("");

    // Trigger bar fill animation
    setTimeout(() => {
      data.distribution.forEach((item, idx) => {
        const fillEl = document.getElementById(`barFill_${idx}`);
        if (fillEl) {
          fillEl.style.width = `${(item.score * 100).toFixed(1)}%`;
        }
      });
    }, 60);
  }

  // 4. Update Engine Footer Text
  const engineText = document.getElementById("engineText");
  if (engineText && data.engine) {
    engineText.innerText = data.engine;
  }
}

// Copy Analysis Results to Clipboard
function copyAnalysisResult() {
  if (!lastResultData) return;
  const { title, content, data } = lastResultData;

  const topName = data.primary_name;
  const topConf = (data.confidence * 100).toFixed(1);
  const textSnippet = title ? title : content.substring(0, 100) + "...";

  const shareText = `[VietNews AI V4 Analysis]\n📌 Bài viết: "${textSnippet}"\n🎯 Dự đoán: ${topName} (${topConf}%)\n⚡ Model: ${data.engine}`;

  navigator.clipboard.writeText(shareText).then(() => {
    showToast("Đã sao chép kết quả phân tích!");
  }).catch(() => {
    showToast("Không thể sao chép kết quả", "error");
  });
}

// Toast Notifications Helper
function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation'}"></i>
    <span>${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Modal Event Handlers
function initModalEvents() {
  const btnInfo = document.getElementById("btnInfoModal");
  const modal = document.getElementById("infoModal");
  const btnClose = document.getElementById("btnCloseModal");

  if (btnInfo && modal) {
    btnInfo.addEventListener("click", () => modal.classList.remove("hidden"));
  }
  if (btnClose && modal) {
    btnClose.addEventListener("click", () => modal.classList.add("hidden"));
  }
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.classList.add("hidden");
    });
  }
}

// Health Check API Server
async function checkApiHealth() {
  try {
    const res = await fetch("/api/stats");
    if (res.ok) {
      const data = await res.json();
      const statusText = document.getElementById("statusText");
      if (statusText && data.engine) {
        statusText.innerText = "VietNews AI V4 — Online";
      }
    }
  } catch (err) {
    console.log("Health check silent fail, using default header");
  }
}
