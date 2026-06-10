document.addEventListener('DOMContentLoaded', function() {
    console.log('良率分析系统已加载');
    
    const logo = document.querySelector('.nav-logo');
    if (logo) {
        let clickCount = 0;
        logo.addEventListener('click', function() {
            clickCount++;
            if (clickCount >= 5) {
                window.location.href = '/factor-analyzer';
                clickCount = 0;
            }
            setTimeout(() => {
                clickCount = 0;
            }, 3000);
        });
    }
});

function formatNumber(num) {
    if (num >= 1000) {
        return num.toLocaleString();
    }
    return num;
}

function showLoading(element) {
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    if (element) {
        element.innerHTML = '<div class="loading">加载中...</div>';
    }
}

function showError(element, message) {
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    if (element) {
        element.innerHTML = `<div class="error">${message}</div>`;
    }
}
