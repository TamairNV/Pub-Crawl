import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-terms',
  standalone: true,
  imports: [RouterLink],
  styleUrls: ['./legal.css'],
  template: `
  <div class="legal"><a routerLink="/" class="back">← Home</a>
  <article class="doc">
    <h2>Terms of use</h2>
    <p class="updated">Last updated 24 November 2026</p>
    <p>CRAWLR is run by Isotopic Studios ("we"). By using it you agree to these terms.</p>
    <h3>Who can use it</h3>
    <p>You must be 18 or over. Organisers are responsible for their crawl: who they invite, the rules they set, and keeping it safe and legal.</p>
    <h3>Drinking</h3>
    <p>CRAWLR is a game for keeping score. It never requires anyone to drink alcohol. Soft drinks count for every challenge. Know your limits, look after each other, and follow the venue's rules and the law. We aren't responsible for what happens on a night out.</p>
    <h3>Your content</h3>
    <p>You own the photos and text you add. You give us permission to store and show them to the people in your crawl so the app works. Don't upload anything illegal, hateful, or anything of people who haven't agreed to it. We can remove content or accounts that break these terms.</p>
    <h3>Payments</h3>
    <p>Paid crawls are a one-off payment per crawl, handled by Stripe. The unlock applies to that crawl only. If something goes wrong with a paid crawl, contact us and we'll sort it out, including a refund where it's fair to.</p>
    <h3>Free-access codes</h3>
    <p>Codes we give out unlock one crawl per use, can have a limited number of uses or an expiry date, and can't be exchanged for money.</p>
    <h3>The service</h3>
    <p>We work hard to keep CRAWLR running, but it's provided as it is, and we can't promise it will always be available or error-free. To the extent the law allows, our liability is limited to what you paid for the crawl in question. Nothing here limits rights you have under UK consumer law.</p>
    <h3>Changes</h3>
    <p>We may update these terms. If the change matters, we'll say so in the app.</p>
    <p>These terms are governed by the law of England and Wales.</p>
  </article></div>`,
})
export class TermsComponent {}
