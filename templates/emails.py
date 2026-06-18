"""
Email templates for CVS lead generation.
"""

from config import config


def initial_outreach(
    first_name: str,
    company: str,
    title: str,
    pain_point: str,
    personalized_line: str,
    demo_url: str = "",
) -> tuple[str, str]:
    """Returns (subject, html_body)."""
    subject = f"I built a demo CRM for {company} — take a look"

    demo_block = ""
    if demo_url:
        demo_block = f"""
<p style="margin: 20px 0;">
  <a href="{demo_url}"
     style="background: #0066ff; color: white; padding: 12px 22px;
     border-radius: 6px; text-decoration: none; font-size: 15px;
     display: inline-block; font-weight: 600;">
    👁 View Your Personalized Demo →
  </a>
</p>
<p style="font-size: 13px; color: #888;">
  (Built specifically for {company} — takes 30 seconds to explore)
</p>"""

    html = f"""
<html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
<p>Hi {first_name},</p>

<p>{personalized_line}</p>

<p>I put together a quick interactive preview of what a custom CRM built specifically
for <strong>{company}</strong> could look like — based on your industry and how companies like yours typically work:</p>

{demo_block}

<p>At <strong>{config.COMPANY_NAME}</strong>, we build custom CRMs and SaaS products for B2B teams —
the kind that actually fit how your team works, not the other way around.</p>

<p>A few things we handle:</p>
<ul>
  <li>Custom CRM tailored to your sales workflow</li>
  <li>SaaS product development — MVP to scale</li>
  <li>Integrations with your existing tools</li>
</ul>

<p>Would a <strong>15-minute call</strong> this week make sense?<br>
<a href="{config.CALENDLY_MEETING_LINK}" style="color: #0066ff;">Grab a slot here →</a></p>

<p>Best,<br>
<strong>{config.SENDER_NAME}</strong><br>
{config.COMPANY_NAME}<br>
<a href="{config.COMPANY_PORTFOLIO_URL}" style="color: #0066ff;">Portfolio</a></p>

<p style="font-size: 11px; color: #999;">
If this isn't relevant, just reply "unsubscribe" and I won't reach out again.
</p>
</body></html>
"""
    return subject, html


def follow_up(
    first_name: str,
    company: str,
    original_subject: str,
    value_prop: str,  # AI-generated, different angle from first email
) -> tuple[str, str]:
    """Returns (subject, html_body) for follow-up email."""
    subject = f"Re: {original_subject}"
    html = f"""
<html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
<p>Hi {first_name},</p>

<p>Just wanted to bump this up in case it got buried. {value_prop}</p>

<p>I know you're busy running {company}, so I'll keep this short:</p>

<p>We recently helped a SaaS company similar to yours <strong>reduce their CRM customization costs by 55%</strong>
while shipping 3x faster. I think we could do the same for your team.</p>

<p>Here's a quick demo of what we built:
<a href="{config.COMPANY_DEMO_URL}" style="color: #4F46E5;">Watch 2-min demo →</a></p>

<p>If the timing is right, grab 15 minutes on my calendar:<br>
<a href="{config.CALENDLY_MEETING_LINK}" style="color: #4F46E5;">{config.CALENDLY_MEETING_LINK}</a></p>

<p>If not now, no worries — I'll check back in a few weeks.</p>

<p>Best,<br>
<strong>{config.SENDER_NAME}</strong><br>
{config.COMPANY_NAME}</p>
</body></html>
"""
    return subject, html


def meeting_confirmation(
    first_name: str,
    company: str,
    demo_url: str = "",
) -> tuple[str, str]:
    """Returns (subject, html_body) for post-reply meeting booking email."""
    subject = f"Let's connect, {first_name} — here's your {company} demo + my calendar"

    demo_block = ""
    if demo_url:
        demo_block = f"""
<p>I also refreshed the personalized demo I built for {company} — take a look before our call:</p>
<p style="margin: 16px 0;">
  <a href="{demo_url}"
     style="background: #0066ff; color: white; padding: 11px 22px;
     border-radius: 6px; text-decoration: none; font-size: 14px;
     display: inline-block; font-weight: 600;">
    👁 View {company}'s Custom Demo →
  </a>
</p>"""

    html = f"""
<html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
<p>Hi {first_name},</p>

<p>Thanks for getting back to me! I'd love to learn more about {company}
and show you concretely what we'd build.</p>

{demo_block}

<p>Grab any slot that works for you:</p>

<p style="margin: 20px 0;">
<a href="{config.CALENDLY_MEETING_LINK}"
   style="background: #16a34a; color: white; padding: 12px 24px;
   border-radius: 6px; text-decoration: none; font-size: 15px; display: inline-block; font-weight: 600;">
📅 Book a 20-Min Strategy Call
</a></p>

<p>Also check out <a href="{config.COMPANY_PORTFOLIO_URL}" style="color: #0066ff;">our portfolio</a>
for recent CRM and SaaS projects.</p>

<p>Looking forward to talking!</p>

<p>Best,<br>
<strong>{config.SENDER_NAME}</strong><br>
{config.COMPANY_NAME}</p>
</body></html>
"""
    return subject, html
