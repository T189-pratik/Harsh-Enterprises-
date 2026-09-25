const modal = document.getElementById("myModal");
const btn = document.getElementById("viewAllBtn");
const span = document.getElementsByClassName("close")[0];
if(btn && modal){
    btn.onclick = () => modal.style.display = "block";
}

if(span && modal){
    span.onclick = () => modal.style.display = "none";
}
window.onclick = (e) => { if(e.target == modal) modal.style.display = "none"; }



document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function() {
        // Remove the active class from all links
        document.querySelectorAll('.nav-link').forEach(item => item.classList.remove('active'));

        // Add active class to the clicked link
        this.classList.add('active');
    });
});


function scrollCards(button, direction) {
    const section = button.closest('.property-section');
    const propertyList = section.querySelector('.property-list');

    // पहिले hidden cards दाखवा
    const hiddenCards = propertyList.querySelectorAll('.hidden');
    hiddenCards.forEach(card => {
        card.classList.remove('hidden');
    });

    // Scroll त्या दिशेने
    const cardWidth = 335; // card width + gap
    const currentScroll = propertyList.scrollLeft;
    const newScroll = currentScroll + (direction * cardWidth);

    propertyList.scrollTo({
        left: newScroll,
        behavior: 'smooth'
    });
}

// Mobile वर touch swipe साठी
document.querySelectorAll('.property-list').forEach(list => {
    let isDown = false;
    let startX;
    let scrollLeft;

    list.addEventListener('mousedown', (e) => {
        isDown = true;
        startX = e.pageX - list.offsetLeft;
        scrollLeft = list.scrollLeft;
    });

    list.addEventListener('mouseleave', () => {
        isDown = false;
    });

    list.addEventListener('mouseup', () => {
        isDown = false;
    });

    list.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - list.offsetLeft;
        const walk = (x - startX) * 2;
        list.scrollLeft = scrollLeft - walk;
    });

    // Touch events for mobile
    list.addEventListener('touchstart', (e) => {
        startX = e.touches[0].pageX - list.offsetLeft;
        scrollLeft = list.scrollLeft;
    });

    list.addEventListener('touchmove', (e) => {
        const x = e.touches[0].pageX - list.offsetLeft;
        const walk = (x - startX) * 2;
        list.scrollLeft = scrollLeft - walk;
    });
});


