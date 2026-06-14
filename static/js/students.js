document.addEventListener('DOMContentLoaded', function () {
    let selectedStudentId = null;

    const formatModal = document.getElementById('formatModal');
    const confirmBtn  = document.getElementById('confirmGenerateBtn');

    if (!formatModal || !confirmBtn) return;

    formatModal.addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;
        selectedStudentId = button.getAttribute('data-student-id');
    });

    confirmBtn.addEventListener('click', function () {
        if (!selectedStudentId) return;

        const formatInput = document.querySelector('input[name="idFormat"]:checked');
        if (!formatInput) return;

        const format = formatInput.value;
        // yahan simple string + concatenation use kiya hai, koi backtick nahi
        const url = "/generate_one/" + selectedStudentId + "?format=" + encodeURIComponent(format);
        window.location.href = url;
    });
});