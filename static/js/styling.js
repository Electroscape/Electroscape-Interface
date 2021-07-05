function relay_override_style(code, lock = false) {
    let status = document.getElementById("status_" + code);
    let sol = document.getElementById("solution_" + code);
    let inp = document.getElementById("input_" + code);
    let old_btn = document.getElementById("btn_" + code);
    let new_btn = document.getElementById("btn_onOff_" + code);

    // if all elements successfully in DOM
    let sucess = status && sol && inp && old_btn && new_btn
    if (sucess) {
        sol.style.display = "none";
        old_btn.disabled = true;
        old_btn.textContent = "LOCKED";
        status.style.borderColor = "#e6c846";

        if (lock) {
            inp.style.color = "#e6c846";
            inp.innerHTML = "OVERRIDE".bold();
        } else {
            inp.style.display = "none";
            new_btn.style.display = "";
        }
    }
}

function print_debugger(line) {
    document.getElementById("TestHere1").innerHTML = line
    var arr = line.split(",");
    if (arr.length == 4 && arr[0].startsWith('!') && arr[arr.length - 1] == "Done.") {
        document.getElementById("TestHere2").innerHTML = arr[1]
        document.getElementById("TestHere3").innerHTML = arr[2]
    } else {
        document.getElementById("TestHere2").innerHTML = arr.length
        document.getElementById("TestHere3").innerHTML = "Different?"
    }
}

function riddle_wrong_solution(code) {
    let inp = document.getElementById("input_" + code);
    if (inp) {
        inp.style.borderColor = "red";
    }
}

function riddle_correct_solution(code, fireworks = true) {
    if (fireworks) {
        var canv = document.getElementById("fireworks_canvas");
        if (canv) {
            canv.style.display = "inline-block";
            setTimeout(function () { canv.style.display = "none" }, 3000);
        }
    }
    let inp = document.getElementById("input_" + code);
    let sol = document.getElementById("solution_" + code);
    let btn = document.getElementById("btn_" + code);
    if (inp && sol && btn) {
        inp.style.borderColor = "green";
        sol.style.display = "none"
        btn.textContent = "LOCKED"
        btn.disabled = true
    }
}

function riddle_update_frontend(relays) {
    for (let rel of relays) {
        let inp = document.getElementById("input_" + rel.code);
        if (inp) {
            if (rel.riddle_status == 'correct' || rel.riddle_status == 'done') {
                riddle_correct_solution(rel.code, (rel.riddle_status == 'correct'))
            } else if (rel.riddle_status == 'wrong') {
                riddle_wrong_solution(rel.code);
            } else {
                inp.style.borderColor = "#555";
            }

            if (rel.riddle_status == 'override') {
                relay_override_style(rel.code, rel.lock_status);
            } else {
                inp.innerHTML = rel.last_message;
            }
        }
    }
}

function postload_styling(code, last_msg, riddle_status, lock) {
    let relay = {
        code: code,
        last_message: last_msg,
        riddle_status: riddle_status,
        lock_status: lock
    };
    riddle_update_frontend([relay]);
}
