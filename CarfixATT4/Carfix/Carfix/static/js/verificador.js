const inputs = document.querySelectorAll(".input-field input"),
      button = document.querySelector("button"),
      hiddenInput = document.getElementById("codigo");

window.addEventListener("load", () => {
    inputs[0].removeAttribute("disabled");
    inputs[0].focus();
});

inputs.forEach((input, index1) => {
    input.addEventListener("keyup", (e) => {
        const currentInput = input,
              nextInput = input.nextElementSibling,
              prevInput = input.previousElementSibling;

        if (currentInput.value.length > 1) {
            currentInput.value = "";
            return;
        }

        if (nextInput && nextInput.hasAttribute("disabled") && currentInput.value !== "") {
            nextInput.removeAttribute("disabled");
            nextInput.focus();
        }

        if (e.key === "Backspace") {
            inputs.forEach((inp, index2) => {
                if (index1 <= index2 && prevInput) {
                    inp.setAttribute("disabled", true);
                    inp.value = "";
                    prevInput.focus();
                }
            });
        }

        // Ativa o botão se todos os campos estiverem preenchidos
        const allFilled = Array.from(inputs).every(inp => inp.value.length === 1);
        if (allFilled) {
            const code = Array.from(inputs).map(inp => inp.value).join('');
            hiddenInput.value = code;
            button.classList.add("active");
            button.disabled = false;
        } else {
            button.classList.remove("active");
            button.disabled = true;
        }
    });
});
