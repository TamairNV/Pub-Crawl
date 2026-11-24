import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-privacy',
  standalone: true,
  imports: [RouterLink],
  styleUrls: ['./legal.css'],
  template: `
  <div class="legal"><a routerLink="/" class="back">← Home</a>
  <article class="doc">
    <h2>Privacy</h2>
    <p class="updated">Last updated 24 November 2026</p>
    <p>Isotopic Studios runs CRAWLR and is responsible for your data. We collect as little as we can.</p>
    <h3>What we keep</h3>
    <ul>
      <li><strong>Your name</strong> (or nickname) and, if you make an account, your password, stored only as a secure hash. Guests who join by QR code just give a name.</li>
      <li><strong>Your crawl</strong>: teams, scores, rules, award votes and tasks.</li>
      <li><strong>Photos and videos you upload</strong>, including when and where they were taken (from the photo's own data), so they can be shown on the crawl's map. Only people in that crawl can see them.</li>
      <li><strong>Payments</strong>: Stripe handles card details. We never see or store your card, only that a crawl was paid for.</li>
    </ul>
    <h3>Cookies</h3>
    <p>One cookie keeps you logged in. Your phone also keeps a copy of the app and the latest scores so it works without signal. No advertising or tracking cookies.</p>
    <h3>Why we use it</h3>
    <p>Only to run your crawl (our legitimate interest and our agreement with you), to take payments, and to keep the service secure (for example, limiting repeated wrong passwords).</p>
    <h3>Who sees it</h3>
    <p>People in your crawl see names, teams, scores and media. The organiser and refs can manage the crawl. We use Stripe for payments and Cloudflare to deliver the site securely. We never sell your data.</p>
    <h3>How long we keep it</h3>
    <p>Photos and videos are deleted after a set time once the crawl is over. Crawls and accounts stay until you or your organiser delete them. Ask us and we'll delete your data.</p>
    <h3>Your rights</h3>
    <p>You can ask to see, correct, export or delete your data, or object to how we use it. You can also complain to the ICO (ico.org.uk).</p>
  </article></div>`,
})
export class PrivacyComponent {}
