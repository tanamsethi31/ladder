# Ladder demo GIF — regenerate with: vhs assets/demo.tape
# Requires the vhs CLI (https://github.com/charmbracelet/vhs) and a working
# `ladder` on PATH. Fully self-contained: every command below is real output
# from a fresh project, no pre-baked fixture file.

Output assets/demo.gif

Require ladder

Set Shell "bash"
Set FontSize 20
Set Width 1200
Set Height 700
Set Padding 24
Set WindowBar Colorful
Set BorderRadius 10
Set TypingSpeed 25ms
Set Theme {"name":"Ladder","black":"#221b16","red":"#d0604f","green":"#93b854","yellow":"#e0a458","blue":"#6fa3a0","magenta":"#c98f7a","cyan":"#6fa3a0","white":"#efe4d3","brightBlack":"#6f6252","brightRed":"#e37a68","brightGreen":"#a8cf6c","brightYellow":"#f0b878","brightBlue":"#8fc0bd","brightMagenta":"#dba48f","brightCyan":"#8fc0bd","brightWhite":"#f7f1e6","background":"#181310","foreground":"#efe4d3","cursor":"#e0a458","selection":"#362c23"}

Hide
Type "rm -rf /tmp/payments-service && mkdir -p /tmp/payments-service && cd /tmp/payments-service && clear"
Enter
Show

Type "ladder init --project 'Payments Service'"
Enter
Sleep 900ms

Type "ladder abandon R002 --reason 'placeholder, replacing with real work below'"
Enter
Sleep 700ms

Type "ladder add 'Choose queue backend' --why 'Retries and backpressure need a durable queue' --context 'Payments must not silently drop jobs'"
Enter
Sleep 800ms

Type "ladder add 'Add retry policy for failed payments' --why 'Payments must not silently fail' --blocked-by R003"
Enter
Sleep 800ms

Type "ladder status"
Enter
Sleep 3000ms

Type "ladder next"
Enter
Sleep 2500ms
