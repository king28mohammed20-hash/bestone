// ===== Best One Luxury Theme - محسن ومبسط =====

class OptimizedLuxuryTheme {
  constructor() {
    this.isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.isMobile = window.innerWidth <= 768;
    this.init();
  }

  init() {
    this.createThemeToggle();
    this.initTheme();
    this.initSimpleAnimations();
    this.initScrollEffects();
    this.fixNavbar();
    this.addUtilityFeatures();
  }

  // ===== زر التبديل البسيط =====
  createThemeToggle() {
    const toggle = document.createElement('button');
    toggle.className = 'theme-toggle';
    toggle.setAttribute('aria-label', 'تبديل الوضع الليلي');
    document.body.appendChild(toggle);

    toggle.addEventListener('click', () => {
      this.toggleTheme();
    });
  }

  // ===== تهيئة الثيم =====
  initTheme() {
    const savedTheme = localStorage.getItem('luxury-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
  }

  // ===== تبديل الثيم =====
  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('luxury-theme', newTheme);
  }

  // ===== أنيميشن بسيط عند التمرير =====
  initSimpleAnimations() {
    // تجاهل الأنيميشن على الجوال أو إذا كان المستخدم يفضل تقليل الحركة
    if (this.isMobile || this.isReducedMotion) {
      return;
    }

    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          // إلغاء مراقبة العنصر لتحسين الأداء
          observer.unobserve(entry.target);
        }
      });
    }, observerOptions);

    // مراقبة العناصر فقط إذا لم تكن مرئية
    document.querySelectorAll('.card, .alert').forEach(el => {
      el.classList.add('animate-on-scroll');
      observer.observe(el);
    });
  }

  // ===== تأثيرات التمرير =====
  initScrollEffects() {
    let lastScrollTop = 0;
    let ticking = false;

    const updateNavbar = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const navbar = document.querySelector('.navbar');
      
      if (!navbar) return;

      // تأثير الشفافية فقط
      if (scrollTop > 50) {
        navbar.style.background = 'rgba(255, 255, 255, 0.98)';
        if (document.documentElement.getAttribute('data-theme') === 'dark') {
          navbar.style.background = 'rgba(15, 23, 42, 0.98)';
        }
      } else {
        navbar.style.background = 'rgba(255, 255, 255, 0.95)';
        if (document.documentElement.getAttribute('data-theme') === 'dark') {
          navbar.style.background = 'rgba(15, 23, 42, 0.95)';
        }
      }

      lastScrollTop = scrollTop;
      ticking = false;
    };

    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(updateNavbar);
        ticking = true;
      }
    });
  }

  // ===== إصلاح مشاكل النافبار =====
  fixNavbar() {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
      // التأكد من أن النافبار ثابت في المكان الصحيح
      navbar.style.position = 'fixed';
      navbar.style.top = '0';
      navbar.style.width = '100%';
      navbar.style.zIndex = '1030';
      
      // إضافة padding للـ body
      document.body.style.paddingTop = navbar.offsetHeight + 'px';
    }

    // إصلاح الدروب داون
    document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
      toggle.addEventListener('click', function(e) {
        e.preventDefault();
        const menu = this.nextElementSibling;
        if (menu && menu.classList.contains('dropdown-menu')) {
          menu.classList.toggle('show');
        }
      });
    });

    // إغلاق الدروب داون عند النقر خارجها
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.dropdown')) {
        document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
          menu.classList.remove('show');
        });
      }
    });
  }

  // ===== ميزات إضافية مفيدة =====
  addUtilityFeatures() {
    // زر العودة للأعلى
    this.createScrollTopButton();
    
    // إخفاء الرسائل تلقائياً
    this.autoHideAlerts();
    
    // تحسين النماذج
    this.enhanceForms();
  }

  // ===== زر العودة للأعلى =====
  createScrollTopButton() {
    const scrollBtn = document.createElement('div');
    scrollBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
    scrollBtn.className = 'scroll-to-top';
    scrollBtn.style.cssText = `
      position: fixed;
      bottom: 30px;
      right: 30px;
      width: 50px;
      height: 50px;
      background: var(--gradient-luxury);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      cursor: pointer;
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s ease;
      z-index: 1030;
      box-shadow: var(--shadow-light);
    `;
    
    document.body.appendChild(scrollBtn);

    // إظهار/إخفاء الزر
    window.addEventListener('scroll', () => {
      if (window.pageYOffset > 300) {
        scrollBtn.style.opacity = '1';
        scrollBtn.style.visibility = 'visible';
      } else {
        scrollBtn.style.opacity = '0';
        scrollBtn.style.visibility = 'hidden';
      }
    });

    // وظيفة العودة للأعلى
    scrollBtn.addEventListener('click', () => {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  }

  // ===== إخفاء الرسائل تلقائياً =====
  autoHideAlerts() {
    document.querySelectorAll('.alert').forEach(alert => {
      // إضافة زر إغلاق إذا لم يكن موجود
      if (!alert.querySelector('.btn-close')) {
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '×';
        closeBtn.className = 'btn-close';
        closeBtn.style.cssText = `
          position: absolute;
          top: 10px;
          right: 15px;
          background: none;
          border: none;
          font-size: 1.5rem;
          cursor: pointer;
          opacity: 0.6;
          transition: opacity 0.2s ease;
        `;
        closeBtn.addEventListener('click', () => {
          alert.style.opacity = '0';
          alert.style.transform = 'translateX(100%)';
          setTimeout(() => alert.remove(), 300);
        });
        closeBtn.addEventListener('mouseover', () => closeBtn.style.opacity = '1');
        closeBtn.addEventListener('mouseout', () => closeBtn.style.opacity = '0.6');
        
        alert.style.position = 'relative';
        alert.appendChild(closeBtn);
      }

      // إخفاء تلقائي بعد 5 ثواني
      setTimeout(() => {
        if (alert.parentNode) {
          alert.style.opacity = '0';
          alert.style.transform = 'translateX(100%)';
          setTimeout(() => {
            if (alert.parentNode) {
              alert.remove();
            }
          }, 300);
        }
      }, 5000);
    });
  }

  // ===== تحسين النماذج =====
  enhanceForms() {
    // تحسين حقول الإدخال
    document.querySelectorAll('.form-control').forEach(input => {
      // تأثير التركيز
      input.addEventListener('focus', function() {
        this.style.borderColor = 'var(--luxury-gold)';
        this.style.boxShadow = '0 0 10px rgba(212, 175, 55, 0.2)';
      });

      input.addEventListener('blur', function() {
        this.style.borderColor = '#e2e8f0';
        this.style.boxShadow = 'none';
      });
    });

    // تحسين الأزرار
    document.querySelectorAll('.btn').forEach(btn => {
      btn.addEventListener('mousedown', function() {
        this.style.transform = 'scale(0.98)';
      });

      btn.addEventListener('mouseup', function() {
        this.style.transform = 'scale(1)';
      });

      btn.addEventListener('mouseleave', function() {
        this.style.transform = 'scale(1)';
      });
    });
  }
}

// ===== تشغيل بسيط عند تحميل الصفحة =====
document.addEventListener('DOMContentLoaded', () => {
  // تأخير قصير لضمان تحميل كل شيء
  setTimeout(() => {
    try {
      new OptimizedLuxuryTheme();
    } catch (error) {
      console.log('Theme initialization skipped:', error.message);
      // في حالة حدوث خطأ، نشغل الوضع الأساسي فقط
      initBasicMode();
    }
  }, 100);
});

// ===== وضع أساسي بدون تأثيرات =====
function initBasicMode() {
  // زر التبديل البسيط فقط
  const toggle = document.createElement('button');
  toggle.className = 'theme-toggle';
  toggle.style.cssText = `
    position: fixed; top: 20px; left: 20px; z-index: 1050;
    width: 50px; height: 25px; border: none; border-radius: 25px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    cursor: pointer; transition: all 0.3s ease;
  `;
  
  const slider = document.createElement('div');
  slider.style.cssText = `
    width: 21px; height: 21px; background: white; border-radius: 50%;
    transition: all 0.3s ease; margin: 2px;
  `;
  
  toggle.appendChild(slider);
  document.body.appendChild(toggle);

  // وظيفة التبديل
  toggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('luxury-theme', newTheme);
    
    if (newTheme === 'dark') {
      slider.style.transform = 'translateX(25px)';
    } else {
      slider.style.transform = 'translateX(0)';
    }
  });

  // تطبيق الثيم المحفوظ
  const savedTheme = localStorage.getItem('luxury-theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  if (savedTheme === 'dark') {
    slider.style.transform = 'translateX(25px)';
  }
}

// ===== تحسين الأداء =====
// إيقاف التأثيرات عند عدم النشاط
let activityTimer;
const pauseAnimations = () => {
  document.body.classList.add('inactive');
};

const resumeAnimations = () => {
  document.body.classList.remove('inactive');
  clearTimeout(activityTimer);
  activityTimer = setTimeout(pauseAnimations, 30000); // 30 ثانية
};

// مراقبة النشاط
['mousemove', 'keydown', 'scroll', 'touchstart'].forEach(event => {
  document.addEventListener(event, resumeAnimations, { passive: true });
});

// CSS للتجميد عند عدم النشاط
const style = document.createElement('style');
style.textContent = `
  .inactive * {
    animation-play-state: paused !important;
  }
`;
document.head.appendChild(style);