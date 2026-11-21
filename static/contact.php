<?php
// Contact form for filipmat.us/about/ : sends the message by email, stores nothing.
// The recipient address lives only on the server, in contact-config.php
// (not in the public repository):  <?php return ['to' => 'name@example.com'];
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function out($ok, $msg, $code = 200) {
    http_response_code($code);
    echo json_encode(['ok' => $ok, 'message' => $msg]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(false, 'method not allowed', 405);

$cfg = @include __DIR__ . '/contact-config.php';
if (!is_array($cfg) || empty($cfg['to'])) out(false, 'the form is not set up yet', 503);

// spam traps: a hidden field people never fill in, and a minimum time on the page
if (!empty($_POST['website'])) out(true, 'thank you');
$t = isset($_POST['t']) ? intval($_POST['t']) : 0;
if ($t > 0 && (time() * 1000 - $t) < 3000) out(true, 'thank you');

$name = trim(mb_substr(strip_tags($_POST['name'] ?? ''), 0, 100));
$email = trim(mb_substr($_POST['email'] ?? '', 0, 200));
$message = trim(mb_substr(strip_tags($_POST['message'] ?? ''), 0, 5000));

if ($name === '' || $message === '') out(false, 'please fill in your name and message', 400);
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) out(false, 'please check your email address', 400);
if (preg_match('/[\r\n]/', $name . $email)) out(false, 'invalid input', 400);

$subject = 'filipmat.us: message from ' . $name;
$body = "Name: $name\nEmail: $email\n\n$message\n\n--\nsent from the contact form on https://filipmat.us/about/\n";
$headers = "From: filipmat.us <web@filipmat.us>\r\n"
         . "Reply-To: " . $email . "\r\n"
         . "Content-Type: text/plain; charset=UTF-8\r\n";

mb_language('uni');
mb_internal_encoding('UTF-8');
$sent = mb_send_mail($cfg['to'], $subject, $body, $headers);
if (!$sent) out(false, 'sorry, sending failed, please try again later', 500);
out(true, 'thank you, your message is on its way');
