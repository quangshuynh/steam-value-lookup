// automatically update the year in the footer
document.addEventListener("DOMContentLoaded", () => {
    const yearSpan = document.getElementById('current-year');
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }
});


// sorting table
function sortTable(order) {
    const table = document.getElementById("games-table");
    const tbody = table.getElementsByTagName("tbody")[0];
    const rows = Array.from(tbody.getElementsByTagName("tr"));

    rows.sort((a, b) => {
        const gameA = a.getElementsByTagName("td")[1].innerText.toLowerCase();
        const gameB = b.getElementsByTagName("td")[1].innerText.toLowerCase();
        const hoursA = parseFloat(a.getElementsByTagName("td")[2].innerText);
        const hoursB = parseFloat(b.getElementsByTagName("td")[2].innerText);

        switch (order) {
            case 'hours-desc':
                return hoursB - hoursA;
            case 'hours-asc':
                return hoursA - hoursB;
            case 'alpha-desc':
                return gameB.localeCompare(gameA);
            case 'alpha-asc':
                return gameA.localeCompare(gameB);
        }
    });

    // re-append rows in sorted order
    rows.forEach(row => tbody.appendChild(row));
}
