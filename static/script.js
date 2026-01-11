document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const form = document.getElementById("reviewForm");
  const resultsDiv = document.getElementById("results");
  const loadingDiv = document.getElementById("loading");
  const downloadDiv = document.getElementById("download");
  const chartContainer = document.getElementById("chart-container");
  const dropArea = document.getElementById("drop-area");
  const fileInput = document.getElementById("fileInput");
  
  // Configuration
  let reviewsPerPage = 15;
  let reviewsData = [];
  let reviewChart = null;

  // Drag & Drop Functionality
  dropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropArea.classList.add("bg-primary", "text-white");
    dropArea.classList.remove("bg-light");
  });
  
  dropArea.addEventListener("dragleave", (e) => {
    e.preventDefault();
    dropArea.classList.remove("bg-primary", "text-white");
    dropArea.classList.add("bg-light");
  });
  
  dropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    fileInput.files = e.dataTransfer.files;
    dropArea.classList.remove("bg-primary", "text-white");
    dropArea.classList.add("bg-light");
    
    // Show selected file name
    if (e.dataTransfer.files.length > 0) {
      const fileName = e.dataTransfer.files[0].name;
      showFileSelected(fileName);
    }
  });

  // File input change handler
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      const fileName = e.target.files[0].name;
      showFileSelected(fileName);
    }
  });

  // Show selected file name
  function showFileSelected(fileName) {
    const fileInfo = document.createElement("div");
    fileInfo.className = "alert alert-info mt-2";
    fileInfo.innerHTML = `<i class="bi bi-file-check"></i> Selected: <strong>${fileName}</strong>`;
    
    // Remove previous file info if exists
    const existingInfo = dropArea.parentNode.querySelector(".alert-info");
    if (existingInfo) existingInfo.remove();
    
    dropArea.parentNode.appendChild(fileInfo);
  }

  // Form Submission Handler
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    // Validate input
    const linkInput = form.querySelector('input[name="link"]').value.trim();
    const fileInput = form.querySelector('input[name="file"]').files[0];
    
    if (!linkInput && !fileInput) {
      showError("Please provide either a URL or upload a CSV file");
      return;
    }
    
    // Show loading state
    showLoading(true);
    clearResults();

    try {
      const formData = new FormData(form);
      const response = await fetch("/process", { 
        method: "POST", 
        body: formData 
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'An error occurred while processing');
      }

      // Store results and render first page
      reviewsData = data.results;
      
      if (reviewsData.length === 0) {
        showError("No reviews found to analyze");
        return;
      }
      
      // Show scraping info banner
      if (data.estimated_total || data.scraping_efficiency) {
        showScrapingInfo(data);
      }
      
      renderPage(1);
      showDownloadButton(data.download_url);
      showChart(data.counts);
      
      // Show success message
      showSuccessMessage(data.total_reviews || reviewsData.length, data);
      
    } catch (error) {
      console.error("Error:", error);
      showError(error.message);
    } finally {
      showLoading(false);
      form.reset();
      // Remove file selection info
      const fileInfo = document.querySelector(".alert-info");
      if (fileInfo) fileInfo.remove();
    }
  });

  // Helper Functions
  function showLoading(show) {
    loadingDiv.style.display = show ? "block" : "none";
  }

  function clearResults() {
    resultsDiv.innerHTML = "";
    downloadDiv.innerHTML = "";
    chartContainer.style.display = "none";
  }

  function showError(message) {
    resultsDiv.innerHTML = `
      <div class="alert alert-danger" role="alert">
        <i class="bi bi-exclamation-triangle"></i>
        <strong>Error:</strong> ${message}
      </div>
    `;
  }

  function showScrapingInfo(data) {
    const scrapingDiv = document.createElement("div");
    scrapingDiv.className = "alert alert-info mb-3";
    scrapingDiv.style.borderLeft = "5px solid #0dcaf0";
    
    let infoHTML = '<h5 class="alert-heading"><i class="bi bi-info-circle"></i> Scraping Summary</h5>';
    
    const totalOnPage = data.estimated_total || 0;
    const fetched = data.total_reviews || 0;
    
    if (totalOnPage > 0) {
      const percentage = ((fetched / totalOnPage) * 100).toFixed(1);
      const efficiency = percentage >= 80 ? 'success' : percentage >= 50 ? 'warning' : 'danger';
      
      infoHTML += `
        <hr>
        <div class="row text-center">
          <div class="col-md-4">
            <h3 class="text-primary mb-0">${totalOnPage.toLocaleString()}</h3>
            <small class="text-muted">Total reviews on product page</small>
          </div>
          <div class="col-md-4">
            <h3 class="text-success mb-0">${fetched.toLocaleString()}</h3>
            <small class="text-muted">Reviews successfully fetched</small>
          </div>
          <div class="col-md-4">
            <h3 class="text-${efficiency} mb-0">${percentage}%</h3>
            <small class="text-muted">Scraping efficiency</small>
          </div>
        </div>
      `;
      
      if (percentage < 100) {
        infoHTML += `
          <div class="alert alert-warning mt-3 mb-0">
            <small><i class="bi bi-exclamation-triangle"></i> 
            <strong>Note:</strong> Some reviews couldn't be fetched. This may be due to pagination limits, 
            login requirements, or anti-scraping measures.</small>
          </div>
        `;
      }
    } else {
      infoHTML += `
        <hr>
        <p class="mb-0">
          <strong>Total reviews fetched:</strong> ${fetched.toLocaleString()}<br>
          <small class="text-muted">Could not detect total review count from product page.</small>
        </p>
      `;
    }
    
    scrapingDiv.innerHTML = infoHTML;
    resultsDiv.insertBefore(scrapingDiv, resultsDiv.firstChild);
  }

  function showSuccessMessage(totalReviews, data) {
    const successDiv = document.createElement("div");
    successDiv.className = "alert alert-success";
    successDiv.style.borderLeft = "5px solid #198754";
    
    let successHTML = `
      <h5 class="alert-heading">
        <i class="bi bi-check-circle-fill"></i> Analysis Complete!
      </h5>
      <hr>
      <p class="mb-2">Successfully analyzed <strong>${totalReviews.toLocaleString()}</strong> reviews.</p>
    `;
    
    // Add classification summary with actual numbers
    if (data.counts) {
      const originalCount = data.counts['Original'] || 0;
      const fakeCount = data.counts['Fake'] || 0;
      const total = originalCount + fakeCount;
      
      const originalPercent = ((originalCount / total) * 100).toFixed(1);
      const fakePercent = ((fakeCount / total) * 100).toFixed(1);
      
      successHTML += `
        <div class="row text-center mt-3">
          <div class="col-md-6">
            <div class="card bg-success bg-opacity-10 border-success">
              <div class="card-body">
                <h2 class="text-success mb-0">${originalCount.toLocaleString()}</h2>
                <p class="mb-0"><strong>Original Reviews</strong></p>
                <small class="text-muted">${originalPercent}% of total</small>
              </div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="card bg-danger bg-opacity-10 border-danger">
              <div class="card-body">
                <h2 class="text-danger mb-0">${fakeCount.toLocaleString()}</h2>
                <p class="mb-0"><strong>Fake Reviews</strong></p>
                <small class="text-muted">${fakePercent}% of total</small>
              </div>
            </div>
          </div>
        </div>
      `;
    }
    
    successDiv.innerHTML = successHTML;
    resultsDiv.insertBefore(successDiv, resultsDiv.firstChild);
    
    // Auto-remove success message after 8 seconds
    setTimeout(() => {
      if (successDiv.parentNode) {
        successDiv.style.transition = 'opacity 0.5s';
        successDiv.style.opacity = '0';
        setTimeout(() => successDiv.remove(), 500);
      }
    }, 8000);
  }

  function showDownloadButton(downloadUrl) {
    downloadDiv.innerHTML = `
      <div class="text-center mt-3">
        <a href="${downloadUrl}" class="btn btn-primary btn-lg">
          <i class="bi bi-download"></i> Download Results CSV
        </a>
      </div>
    `;
  }

  // Render paginated results
  function renderPage(page) {
    const start = (page - 1) * reviewsPerPage;
    const end = start + reviewsPerPage;
    const slice = reviewsData.slice(start, end);

    let html = `
      <div class="mt-4">
        <h4 class="text-center mb-4">
          <i class="bi bi-list-check"></i> Analysis Results
        </h4>
        <p class="text-center text-muted mb-4">
          Showing ${start + 1}-${Math.min(end, reviewsData.length)} of ${reviewsData.length} reviews
        </p>
      </div>
    `;

    slice.forEach((item, index) => {
      const isOriginal = item.prediction === "Original";
      const alertClass = isOriginal ? "alert-success" : "alert-danger";
      const icon = isOriginal ? "bi-check-circle" : "bi-exclamation-triangle";
      const badgeClass = isOriginal ? "badge-success" : "badge-danger";
      
      html += `
        <div class="alert ${alertClass} mb-3 border-0 shadow-sm" role="alert">
          <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
              <div class="d-flex align-items-center mb-2">
                <i class="bi ${icon} me-2"></i>
                <span class="badge ${badgeClass} fs-6">${item.prediction}</span>
              </div>
              <p class="mb-0">${item.review}</p>
            </div>
          </div>
        </div>
      `;
    });

    // Add pagination if needed
    const totalPages = Math.ceil(reviewsData.length / reviewsPerPage);
    if (totalPages > 1) {
      html += generatePagination(page, totalPages);
    }

    resultsDiv.innerHTML = html;
  }

  // Generate pagination HTML
  function generatePagination(currentPage, totalPages) {
    let paginationHTML = `
      <nav class="mt-4">
        <ul class="pagination justify-content-center">
    `;
    
    // Previous button
    if (currentPage > 1) {
      paginationHTML += `
        <li class="page-item">
          <a class="page-link" href="#" onclick="window.renderPage(${currentPage - 1})">
            <i class="bi bi-chevron-left"></i> Previous
          </a>
        </li>
      `;
    }
    
    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
      paginationHTML += `
        <li class="page-item">
          <a class="page-link" href="#" onclick="window.renderPage(1)">1</a>
        </li>
      `;
      if (startPage > 2) {
        paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
      }
    }
    
    for (let i = startPage; i <= endPage; i++) {
      paginationHTML += `
        <li class="page-item ${i === currentPage ? 'active' : ''}">
          <a class="page-link" href="#" onclick="window.renderPage(${i})">${i}</a>
        </li>
      `;
    }
    
    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
      }
      paginationHTML += `
        <li class="page-item">
          <a class="page-link" href="#" onclick="window.renderPage(${totalPages})">${totalPages}</a>
        </li>
      `;
    }
    
    // Next button
    if (currentPage < totalPages) {
      paginationHTML += `
        <li class="page-item">
          <a class="page-link" href="#" onclick="window.renderPage(${currentPage + 1})">
            Next <i class="bi bi-chevron-right"></i>
          </a>
        </li>
      `;
    }
    
    paginationHTML += `</ul></nav>`;
    return paginationHTML;
  }

  // Chart.js visualization - FIXED
  function showChart(counts) {
    chartContainer.style.display = "block";
    const ctx = document.getElementById("reviewChart").getContext("2d");

    if (reviewChart) {
      reviewChart.destroy();
    }

    // Ensure we have proper labels and data
    const labels = [];
    const data = [];
    const backgroundColors = [];
    
    // Extract Original and Fake counts with proper colors
    if (counts['Original'] !== undefined) {
      labels.push('Original');
      data.push(counts['Original']);
      backgroundColors.push('#28a745'); // Green for Original
    }
    
    if (counts['Fake'] !== undefined) {
      labels.push('Fake');
      data.push(counts['Fake']);
      backgroundColors.push('#dc3545'); // Red for Fake
    }
    
    // Fallback if keys are different
    if (labels.length === 0) {
      Object.keys(counts).forEach(key => {
        labels.push(key);
        data.push(counts[key]);
        // Determine color based on key name
        if (key.toLowerCase().includes('original') || key.toLowerCase().includes('real')) {
          backgroundColors.push('#28a745');
        } else {
          backgroundColors.push('#dc3545');
        }
      });
    }

    const total = data.reduce((a, b) => a + b, 0);

    reviewChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: backgroundColors,
          borderWidth: 3,
          borderColor: "#fff",
          hoverBorderWidth: 4,
          hoverBackgroundColor: backgroundColors
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { 
            position: "bottom",
            labels: {
              padding: 20,
              font: { size: 14, weight: 'bold' },
              generateLabels: function(chart) {
                const original = Chart.defaults.plugins.legend.labels.generateLabels(chart);
                return original.map((label, index) => {
                  const percentage = ((data[index] / total) * 100).toFixed(1);
                  label.text = `${labels[index]}: ${data[index]} reviews (${percentage}%)`;
                  return label;
                });
              }
            }
          },
          title: { 
            display: true, 
            text: `Review Classification Summary (${total} total reviews)`,
            font: { size: 16, weight: 'bold' },
            padding: 20
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = labels[context.dataIndex];
                const value = context.parsed;
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value} reviews (${percentage}%)`;
              }
            }
          }
        },
        cutout: '50%'
      }
    });
  }

  // Expose renderPage function globally for pagination
  window.renderPage = renderPage;
  
  // Add smooth scrolling to results
  window.renderPage = function(page) {
    renderPage(page);
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
});