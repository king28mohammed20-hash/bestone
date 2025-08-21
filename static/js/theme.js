// ===== تأثيرات الظهور المتقدمة =====
class ModernAnimations {
  constructor() {
    this.initScrollAnimations();
    this.initCardHovers();
    this.initFormAnimations();
    this.initNavbarEffects();
    this.initLoadingAnimations();
  }

  // تأثيرات الظهور عند التمرير
  initScrollAnimations() {
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal');
          // إضافة تأخير متدرج للعناصر
          const delay = Array.from(entry.target.parentNode.children).indexOf(entry.target) * 100;
          entry.target.style.animationDelay = `${delay}ms`;
        }
      });
    }, observerOptions);

    // مراقبة جميع البطاقات والعناصر المهمة
    document.querySelectorAll('.card, .alert, .btn-lg, .stats-section .col').forEach(el => {
      observer.observe(el);
    });
  }

  // تأثيرات تفاعلية للبطاقات
  initCardHovers() {
    document.querySelectorAll('.card').forEach(card => {
      card.addEventListener('mouseenter', (e) => {
        // تأثير الإضاءة
        this.createRippleEffect(e.currentTarget, e);
        
        // تحريك العناصر الداخلية
        const img = card.querySelector('img');
        if (img) {
          img.style.transform = 'scale(1.05) rotate(1deg)';
        }
      });

      card.addEventListener('mouseleave', (e) => {
        const img = card.querySelector('img');
        if (img) {
          img.style.transform = 'scale(1) rotate(0deg)';
        }
      });

      // تأثير النقر
      card.addEventListener('click', (e) => {
        this.createClickEffect(e.currentTarget, e);
      });
    });
  }

  // تأثير الموجة عند التمرير
  createRippleEffect(element, event) {
    const ripple = document.createElement('span');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.cssText = `
      position: absolute;
      width: ${size}px;
      height: ${size}px;
      left: ${x}px;
      top: ${y}px;
      background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
      border-radius: 50%;
      transform: scale(0);
      animation: ripple 0.6s ease-out;
      pointer-events: none;
      z-index: 1;
    `;
    
    element.style.position = 'relative';
    element.appendChild(ripple);
    
    setTimeout(() => {
      if (ripple.parentNode) {
        ripple.remove();
      }
    }, 600);
  }

  // تأثير النقر
  createClickEffect(element, event) {
    element.style.transform = 'scale(0.98)';
    setTimeout(() => {
      element.style.transform = 'scale(1)';
    }, 150);
  }

  // تحسين النماذج
  initFormAnimations() {
    // تأثيرات حقول الإدخال
    document.querySelectorAll('.form-control').forEach(input => {
      // إضافة تسمية عائمة
      this.createFloatingLabel(input);
      
      input.addEventListener('focus', (e) => {
        this.animateFormFocus(e.target, true);
      });
      
      input.addEventListener('blur', (e) => {
        this.animateFormFocus(e.target, false);
      });
      
      input.addEventListener('input', (e) => {
        this.validateInput(e.target);
      });
    });

    // تحسين الأزرار
    document.querySelectorAll('.btn').forEach(btn => {
      btn.addEventListener('mousedown', () => {
        btn.style.transform = 'scale(0.95)';
      });
      
      btn.addEventListener('mouseup', () => {
        btn.style.transform = 'scale(1)';
      });
      
      btn.addEventListener('mouseleave', () => {
        btn.style.transform = 'scale(1)';
      });
    });
  }

  // إنشاء تسمية عائمة
  createFloatingLabel(input) {
    const label = input.previousElementSibling;
    if (label && label.tagName === 'LABEL') {
      label.classList.add('floating-label');
      
      // تحديث حالة التسمية
      const updateLabel = () => {
        if (input.value || input === document.activeElement) {
          label.classList.add('active');
        } else {
          label.classList.remove('active');
        }
      };
      
      input.addEventListener('focus', updateLabel);
      input.addEventListener('blur', updateLabel);
      input.addEventListener('input', updateLabel);
      
      // تطبيق الحالة الأولية
      updateLabel();
    }
  }

  // تأثيرات التركيز
  animateFormFocus(input, isFocused) {
    const parent = input.parentElement;
    
    if (isFocused) {
      parent.classList.add('form-focused');
      input.style.transform = 'translateY(-2px)';
      input.style.boxShadow = '0 8px 25px rgba(99, 102, 241, 0.15)';
    } else {
      parent.classList.remove('form-focused');
      input.style.transform = 'translateY(0)';
      input.style.boxShadow = 'none';
    }
  }

  // التحقق من صحة الإدخال
  validateInput(input) {
    const value = input.value;
    const type = input.type;
    
    // إزالة الحالات السابقة
    input.classList.remove('valid', 'invalid');
    
    if (value.length === 0) return;
    
    let isValid = true;
    
    // قواعد التحقق
    switch(type) {
      case 'email':
        isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
        break;
      case 'tel':
        isValid = /^(\+966|0)?[5-9][0-9]{8}$/.test(value.replace(/\s/g, ''));
        break;
      case 'password':
        isValid = value.length >= 6;
        break;
      default:
        isValid = value.length >= 2;
    }
    
    input.classList.add(isValid ? 'valid' : 'invalid');
  }

  // تأثيرات شريط التنقل
  initNavbarEffects() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    
    let lastScrollTop = 0;
    let ticking = false;
    
    const updateNavbar = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      
      // تأثير الشفافية
      if (scrollTop > 50) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
      
      // تأثير الإخفاء/الإظهار
      if (scrollTop > lastScrollTop && scrollTop > 100) {
        navbar.style.transform = 'translateY(-100%)';
      } else {
        navbar.style.transform = 'translateY(0)';
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

  // تأثيرات التحميل
  initLoadingAnimations() {
    // مؤشر التحميل للنماذج
    document.querySelectorAll('form').forEach(form => {
      form.addEventListener('submit', (e) => {
        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn) {
          this.showLoadingState(submitBtn);
        }
      });
    });
    
    // تحميل تدريجي للصور
    this.lazyLoadImages();
  }

  // حالة التحميل للأزرار
  showLoadingState(button) {
    const originalText = button.innerHTML;
    const originalWidth = button.offsetWidth;
    
    button.style.width = originalWidth + 'px';
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري المعالجة...';
    button.disabled = true;
    
    // استعادة الحالة الأصلية بعد 5 ثوان (احتياط)
    setTimeout(() => {
      button.innerHTML = originalText;
      button.disabled = false;
      button.style.width = 'auto';
    }, 5000);
  }

  // تحميل الصور التدريجي
  lazyLoadImages() {
    const imageObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          const src = img.dataset.src;
          
          if (src) {
            img.src = src;
            img.classList.add('loaded');
            imageObserver.unobserve(img);
          }
        }
      });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
      imageObserver.observe(img);
    });
  }
}

// ===== مدير الثيم =====
class ThemeManager {
  constructor() {
    this.currentTheme = localStorage.getItem('theme') || 'light';
    this.init();
  }

  init() {
    this.applyTheme(this.currentTheme);
    this.createThemeToggle();
  }

  createThemeToggle() {
    const toggle = document.createElement('button');
    toggle.className = 'theme-toggle-btn';
    toggle.innerHTML = '<i class="fas fa-moon"></i>';
    toggle.setAttribute('aria-label', 'تبديل الوضع الليلي');
    
    toggle.style.cssText = `
      position: fixed;
      top: 20px;
      left: 20px;
      z-index: 1050;
      width: 50px;
      height: 50px;
      border: none;
      border-radius: 50%;
      background: var(--gradient-primary);
      color: white;
      cursor: pointer;
      transition: all 0.3s ease;
      box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    `;
    
    toggle.addEventListener('click', () => {
      this.toggleTheme();
    });
    
    document.body.appendChild(toggle);
    this.updateToggleIcon(toggle);
  }

  toggleTheme() {
    this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    this.applyTheme(this.currentTheme);
    localStorage.setItem('theme', this.currentTheme);
    
    const toggle = document.querySelector('.theme-toggle-btn');
    if (toggle) {
      this.updateToggleIcon(toggle);
    }
  }

  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    
    // تحديث متغيرات CSS
    const root = document.documentElement;
    if (theme === 'dark') {
      root.style.setProperty('--bg-primary', '#0f172a');
      root.style.setProperty('--bg-secondary', '#1e293b');
      root.style.setProperty('--text-primary', '#f8fafc');
      root.style.setProperty('--text-secondary', '#cbd5e1');
    } else {
      root.style.setProperty('--bg-primary', '#ffffff');
      root.style.setProperty('--bg-secondary', '#f8fafc');
      root.style.setProperty('--text-primary', '#1e293b');
      root.style.setProperty('--text-secondary', '#64748b');
    }
  }

  updateToggleIcon(toggle) {
    const icon = toggle.querySelector('i');
    if (this.currentTheme === 'dark') {
      icon.className = 'fas fa-sun';
    } else {
      icon.className = 'fas fa-moon';
    }
  }
}

// ===== مساعدات إضافية =====
class UtilityHelpers {
  static init() {
    this.createScrollToTop();
    this.enhanceTooltips();
    this.autoHideAlerts();
    this.improveAccessibility();
  }

  // زر العودة للأعلى
  static createScrollToTop() {
    const scrollBtn = document.createElement('button');
    scrollBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
    scrollBtn.className = 'scroll-to-top';
    scrollBtn.setAttribute('aria-label', 'العودة للأعلى');
    
    scrollBtn.style.cssText = `
      position: fixed;
      bottom: 30px;
      right: 30px;
      width: 50px;
      height: 50px;
      border: none;
      border-radius: 50%;
      background: var(--brand-primary);
      color: white;
      cursor: pointer;
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s ease;
      z-index: 1030;
      box-shadow: 0 4px 15px rgba(0,0,0,0.2);
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

  // تحسين التولتيبس
  static enhanceTooltips() {
    document.querySelectorAll('[title]').forEach(element => {
      const title = element.getAttribute('title');
      element.removeAttribute('title');
      
      const tooltip = document.createElement('div');
      tooltip.className = 'custom-tooltip';
      tooltip.textContent = title;
      tooltip.style.cssText = `
        position: absolute;
        background: #333;
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 14px;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.3s ease;
        z-index: 1060;
        white-space: nowrap;
      `;
      
      document.body.appendChild(tooltip);
      
      element.addEventListener('mouseenter', (e) => {
        const rect = e.target.getBoundingClientRect();
        tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
        tooltip.style.opacity = '1';
      });
      
      element.addEventListener('mouseleave', () => {
        tooltip.style.opacity = '0';
      });
    });
  }

  // إخفاء التنبيهات تلقائياً
  static autoHideAlerts() {
    document.querySelectorAll('.alert').forEach(alert => {
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

  // تحسين إمكانية الوصول
  static improveAccessibility() {
    // إضافة مؤشرات لوحة المفاتيح
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        document.body.classList.add('keyboard-navigation');
      }
    });
    
    document.addEventListener('click', () => {
      document.body.classList.remove('keyboard-navigation');
    });
    
    // تحسين التنقل بلوحة المفاتيح
    document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
      toggle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggle.click();
        }
      });
    });
  }
}

// ===== CSS إضافي =====
const additionalStyles = `
  @keyframes ripple {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
  
  .floating-label {
    transition: all 0.3s ease;
    transform-origin: left top;
  }
  
  .floating-label.active {
    transform: translateY(-20px) scale(0.8);
    color: var(--brand-primary);
  }
  
  .form-focused {
    position: relative;
  }
  
  .form-control.valid {
    border-color: #10b981;
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.2);
  }
  
  .form-control.invalid {
    border-color: #ef4444;
    box-shadow: 0 0 10px rgba(239, 68, 68, 0.2);
  }
  
  .navbar.scrolled {
    background: rgba(255, 255, 255, 0.98) !important;
    backdrop-filter: blur(20px);
  }
  
  img[data-src]:not(.loaded) {
  opacity: 0;
}

img[data-src].loaded {
  opacity: 1;
  transition: opacity 0.3s ease;
}
  
  .keyboard-navigation *:focus {
    outline: 2px solid var(--brand-primary);
    outline-offset: 2px;
  }
  
  .custom-tooltip {
    font-family: 'Tajawal', sans-serif;
  }
  
  @media (prefers-reduced-motion: reduce) {
    * {
      animation: none !important;
      transition: none !important;
    }
  }
`;

// إضافة CSS للصفحة
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);

// ===== التشغيل =====
document.addEventListener('DOMContentLoaded', () => {
  try {
    new ModernAnimations();
    new ThemeManager();
    UtilityHelpers.init();
    
    console.log('✅ تم تحميل Theme.js بنجاح');
  } catch (error) {
    console.error('❌ خطأ في تحميل Theme.js:', error);
  }
});

// تصدير للاستخدام الخارجي
window.ModernAnimations = ModernAnimations;
window.ThemeManager = ThemeManager;
window.UtilityHelpers = UtilityHelpers;