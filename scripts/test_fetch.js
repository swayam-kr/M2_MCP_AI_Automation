const url = "https://m2-groww-weekly-digest.streamlit.app/health";

async function testFetch() {
  try {
    const res1 = await fetch(url, { redirect: "manual" });
    console.log("Status:", res1.status);
    console.log("Headers:", res1.headers);
    if (res1.status === 303) {
      const cookie = res1.headers.get("set-cookie");
      const location = res1.headers.get("location");
      console.log("Cookie:", cookie);
      console.log("Location:", location);
      
      const res2 = await fetch(location, { redirect: "manual", headers: { "Cookie": cookie }});
      console.log("Status 2:", res2.status);
      console.log("Headers 2:", res2.headers);
      if (res2.status === 303) {
        const finalLoc = res2.headers.get("location");
        console.log("Final Location:", finalLoc);
        const finalRes = await fetch(finalLoc, { headers: { "Cookie": cookie }});
        console.log("Final Status:", finalRes.status);
        console.log("Body:", await finalRes.text());
      }
    }
  } catch(e) {
    console.error(e);
  }
}
testFetch();
