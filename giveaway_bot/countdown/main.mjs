function renderWinner(msg) {
    let winner_els = document.getElementsByTagName("winner");
    let last_digest = document.getElementById("last-digest");
    let current_digest = document.getElementById("current-digest");
    /*let current_seed = document.getElementById("current-seed");*/
    let message_text = document.getElementById("message-text");

    last_digest.textContent = msg.last_digest;
    current_digest.textContent = msg.current_digest;
    /*current_seed.textContent = msg.current_seed;*/
    message_text.textContent = msg.chat_message.message_text;

    Array.prototype.map.call(msg.top5_by_prize, (vector_registration, index) => {
        let [winner1, ...rest] = vector_registration;
        let [vector1, registration1] = winner1;

        let prize_title_els = winner_els[index].getElementsByTagName("strong");

        Array.prototype.map.call(prize_title_els, (el) => {
            el.textContent = registration1.prize_title;
        });

        let successor_els = winner_els[index].getElementsByTagName("pre");

        Array.prototype.map.call(successor_els, (el, index) => {
            let [vector, registration] = vector_registration[index];

            el.textContent = registration.discord_username;
            if (registration.verified == 1) {
                el.style.color = "inherit";
            } else {
                el.style.color = "red";
            }
        });
    });
}


function nn(n){
    return n > 9 ? n.toString(): "0" + n.toString();
}


function renderTimer(delta) {
    let date = new Date(delta * 1000);
    let hh = date.getUTCHours();
    let mm = date.getUTCMinutes();
    let ss = date.getUTCSeconds();

    let hh_el = document.getElementById("hh");
    let mm_el = document.getElementById("mm");
    let ss_el = document.getElementById("ss");

    hh_el.textContent = `${nn(hh)}`;
    mm_el.textContent = `${nn(mm)}`;
    ss_el.textContent = `${nn(ss)}`;
}

function connect() {
    const socket = (() => {
        if (location.hostname === "localhost") {
            return new WebSocket('ws://localhost:8000');
        } else {
            return new WebSocket('ws://bluespan.gg:8000');
        }
    })();

    if (window.location.hash === "#white") {
        document.body.style.color = "white";
    }

    socket.addEventListener('connect', function (event) {
        console.log("connect");
    });

    socket.addEventListener('message', function (event) {
        let msg = JSON.parse(event.data);
        if (msg.event == "tick") {
            renderTimer(msg.delta);
        } else if (msg.event == "winner") {
            console.log(msg);
            renderWinner(msg);
        } else {
            console.log("unhandled event: " + msg.event);
        }
    });

    socket.addEventListener('close', function (event) {
        console.log("reconnect");
        connect();
    });
}

connect();
