// DELETE DATA POPUP ON HOME PAGE
(function () {
  const deleteBtn = document.getElementById('deleteBtnHome');
  const deleteForm = document.getElementById('deleteFormHome');

  if (deleteBtn && deleteForm) {
    deleteBtn.addEventListener('click', function () {
      const ok = confirm("Are you sure you want to delete all records in data/students.csv?");
      if (ok) {
        deleteForm.submit();
      }
    });
  }
})();

// ADD STUDENT FORM VALIDATION
(function () {
  const form = document.getElementById('studentForm');
  if (!form) return;

  const studentCodeInput = document.getElementById('student_code');
  const contactInput = document.getElementById('contact_no');
  const photoDisplay = document.getElementById('photo_filename_display');
  const fullNameInput = document.getElementById('full_name');

  function digitsOnly(e) {
    e.target.value = e.target.value.replace(/\D/g, '').slice(0, 10);
  }

  if (studentCodeInput) studentCodeInput.addEventListener('input', digitsOnly);
  if (contactInput) contactInput.addEventListener('input', digitsOnly);

  function updatePhotoName() {
    const code = studentCodeInput.value;
    if (code.length === 10) {
      photoDisplay.value = code + '.jpg';
    } else {
      photoDisplay.value = '';
    }
  }
  if (studentCodeInput) studentCodeInput.addEventListener('input', updatePhotoName);

  // Simple name pattern check: at least 2 words (Last, First Middle)
  function validName(name) {
    const parts = name.trim().split(/\s+/);
    return parts.length >= 2;
  }

  form.addEventListener('submit', function (e) {
    const code = studentCodeInput.value.trim();
    const contact = contactInput.value.trim();
    const name = fullNameInput.value.trim();

    let msg = '';

    if (!validName(name)) {
      msg = 'Name must be in format: Last First Middle (at least Last and First).';
    } else if (code.length !== 10) {
      msg = 'Student Code must be exactly 10 digits.';
    } else if (contact.length !== 10) {
      msg = 'Contact number must be exactly 10 digits.';
    }

    if (msg) {
      e.preventDefault();
      let box = document.getElementById('clientMessage');
      if (!box) {
        box = document.createElement('p');
        box.id = 'clientMessage';
        box.className = 'msg error';
        form.insertBefore(box, form.firstChild);
      }
      box.textContent = msg;
    }
  });
})();