/** Interact through the parked-confirmation UI in isolated browser rehearsals. */
export async function parkDriver(page, truckId) {
  const read = async id => {
    const response = await page.request.get(new URL(`/api/drive/${id}`, page.url()).toString());
    if (!response.ok()) throw new Error(`Driver snapshot ${id}: HTTP ${response.status()}`);
    return response.json();
  };
  await page.locator('.drive-workspace').waitFor();
  // New Drive mounts start on the demo vehicle T01.
  const initial = await read('T01');
  if (initial.focus.interaction_allowed) await page.getByRole('button', {name:'Lock for driving',exact:true}).waitFor();
  else {
    await page.getByRole('button', {name:'Confirm safely parked',exact:true}).click();
    await page.getByRole('button', {name:'Lock for driving',exact:true}).waitFor();
  }
  const selector = page.getByLabel('Simulated driver truck', {exact:true});
  if (await selector.inputValue() !== truckId) {
    const target = await read(truckId);
    await selector.selectOption(truckId);
    if (!target.focus.interaction_allowed) await page.getByRole('button', {name:'Confirm safely parked',exact:true}).click();
    await page.getByRole('button', {name:'Lock for driving',exact:true}).waitFor();
    await selector.waitFor();
  }
}
