
document.addEventListener('DOMContentLoaded', function() {

    // Animate elements on scroll
    const animateOnScroll = document.querySelectorAll('.animate-on-scroll');
    
    const checkScroll = function() {
        animateOnScroll.forEach(el => {
            const rect = el.getBoundingClientRect();
            const windowHeight = window.innerHeight || document.documentElement.clientHeight;
            if (rect.top <= windowHeight * 0.75 && rect.bottom >= 0) {
                el.classList.add('show');
            }
        });
    };

    window.addEventListener('scroll', checkScroll);
    checkScroll(); // Check on load

    // Add hover effect to navbar items
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});
