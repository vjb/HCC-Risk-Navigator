import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Record video into the assets directory
        context = await browser.new_context(
            record_video_dir="assets/",
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        print("Navigating to Prompt Opinion...")
        await page.goto("https://app.promptopinion.ai/account/login?passwordRequired=true")
        
        try:
            email_input = page.get_by_placeholder("Email", exact=False)
            await email_input.wait_for(timeout=10000)
            await email_input.fill("vjbeltrani@gmail.com")
            await page.keyboard.press("Enter")
        except Exception as e:
            print("Email input not found or already filled:", e)
            
        try:
            password_input = page.get_by_placeholder("Password", exact=False)
            await password_input.wait_for(timeout=10000)
            await password_input.fill("Q&eKE6bEFc5voBdc")
            await page.keyboard.press("Enter")
            # Wait for dashboard to load after login
            await page.wait_for_url("**/workspaces/**", timeout=20000)
        except Exception as e:
            print("Password input not found or failed:", e)
        
        print("Logged in. Waiting for dashboard...")
        await page.wait_for_selector("text=Clinical Orchestrator", timeout=30000)
        await page.get_by_text("Clinical Orchestrator").click()
        
        # Wait for chat input
        await page.wait_for_selector("textarea", timeout=15000)
        
        print("Sending Prompt 1...")
        prompt1 = "Run a baseline audit on our newest FHIR patient cohort and show me the scorecard. I need to see the current RAF value of the group and identify exactly which patients have clinical notes attached that are ready for gap analysis."
        await page.fill("textarea", prompt1)
        await page.keyboard.press("Enter")
        
        # Wait for Orchestrator response
        await page.wait_for_selector("text=Tamara Williams", timeout=60000)
        await page.wait_for_timeout(3000)
        
        print("Sending Prompt 2...")
        prompt2 = "Run the HCC gap analysis audits on the patients flagged as 'Ready for Audit'. I need to see the exact gap descriptions, the vectorstore citations proving the codes, and the projected revenue impact."
        await page.fill("textarea", prompt2)
        await page.keyboard.press("Enter")
        
        # Wait for Risk Navigator response
        await page.wait_for_selector("text=E11.40", timeout=60000)
        await page.wait_for_timeout(3000)
        
        print("Sending Prompt 3...")
        prompt3 = "Verify the clinical gaps identified by the HCC Risk Navigator against CMS M.E.A.T. standards. Use your PubMed access to ensure the prescribed treatments legitimately match the proposed diagnosis. Then, compile the findings into a complete 5Ts deliverable. Explicitly calculate the total projected RAF delta and the final revenue impact at $10,000 per 1.0 RAF. List out the verified physician queries. Address the queries to \"Dr. Sarah Jenkins, MD\" and ensure you cite the exact FHIR DocumentReference IDs."
        await page.fill("textarea", prompt3)
        await page.keyboard.press("Enter")
        
        # Wait for Compliance Reviewer response
        await page.wait_for_selector("text=$9,540/year", timeout=60000)
        await page.wait_for_timeout(5000) 
        
        # Close to save video
        await context.close()
        await browser.close()
        print("Video successfully saved in assets/")

if __name__ == "__main__":
    asyncio.run(run())
