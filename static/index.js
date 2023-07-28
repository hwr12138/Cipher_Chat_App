(function () {
    "use strict";
    let contentArea = document.querySelector('.content');
    const message = document.querySelector('.message');
    const button = document.querySelector('.confirm');

    button.addEventListener('click', function () {
        let line = document.createElement('p');
        let text = document.createTextNode(message.value);
        message.value='';
        line.appendChild(text);
        contentArea.appendChild(line);
    });
})();