// Function to make an XMLHttpRequest to refresh the party content
async function refreshPartyContent(globaljson) {
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState === 4 && this.status === 200) {
      try {var notes=document.getElementById('enemynotes').innerHTML;
        localStorage.setItem(document.getElementById('speciesname2').innerHTML, notes);
        var notesl=[];
        for (item in [0,1,2,3,4,5]) {notesl[item]=document.getElementById('stat'+item).innerHTML}}
      catch(err) {}
      var parser = new DOMParser();
      var responseDoc = parser.parseFromString(this.responseText, 'text/html');
      var newPokemonDivs = responseDoc.querySelectorAll("#party .pokemon");
      // Check if activeIndex is still valid
      if (activeIndex >= newPokemonDivs.length) {activeIndex = 0;} // Reset to 0 if invalid
      setActivePokemon(newPokemonDivs,activeIndex);
      var partyContent = responseDoc.getElementById('party').innerHTML;
      document.getElementById('party').innerHTML = partyContent;
      try {//refresh notes
        if (["","-",undefined].includes(notes)==false) {
          globaljson[document.getElementById('speciesname2').innerHTML]["notes"]=notes}
        if (globaljson[document.getElementById("speciesname2").innerHTML]["notes"]!=="") {
          document.getElementById('enemynotes').innerHTML = globaljson[document.getElementById('speciesname2').innerHTML]["notes"]
        } else {document.getElementById('enemynotes').innerHTML="-"}
        //stats 
        for (item in [0,1,2,3,4,5]) {
          if (["","_",undefined].includes(notes)==false) {
            globaljson[document.getElementById('speciesname2').innerHTML]["stats"][item]=notesl[item]}
          if (globaljson[document.getElementById("speciesname2").innerHTML]["stats"][item]!=="") {
            document.getElementById('stat'+item).innerHTML = globaljson[document.getElementById('speciesname2').innerHTML]["stats"][item]
          } else {document.getElementById('stat'+item).innerHTML="_"}}
        savenotes(globaljson)}
      catch(err) {}}};
  xhttp.open("GET", "tracker.html", true); // Replace with your server endpoint
  xhttp.send();}
async function savenotes(globaljson) {
  var xhr = new XMLHttpRequest();
  xhr.open("POST", "tracker.html", true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(JSON.stringify(globaljson));}
// Function to handle button clicks
function handleButtonClick(event) {
  var pokemonDivs = document.querySelectorAll("#party .pokemon");
  // Add hidden class to the currently active pokemon div
  pokemonDivs[activeIndex].classList.add("hidden");
  if (event.target.id === "previous-button") {
    activeIndex = (activeIndex === 0) ? pokemonDivs.length - 1 : activeIndex - 1;
  } else if (event.target.id === "next-button") {
    activeIndex = (activeIndex === pokemonDivs.length - 1) ? 0 : activeIndex + 1;}
  // Remove hidden class from the new active pokemon div
  pokemonDivs[activeIndex].classList.remove("hidden");
  setActivePokemon(pokemonDivs,activeIndex);}
// Function to get the index of the active pokemon div
function getActivePokemonIndex(pokemonDivs) {
  for (var i = 0; i < pokemonDivs.length; i++) {
    if (!pokemonDivs[i].classList.contains("hidden")) {return i;}}
  return 0;} // Return 0 if no active pokemon found
// Set initial active index from memory (or default to 0)
var activeIndex = parseInt(localStorage.getItem("activeIndex")) || 0;
var stat= localStorage.getItem("stat") || "";
var pokemonDivs = document.querySelectorAll("#party .pokemon");
setActivePokemon(pokemonDivs,activeIndex);
// Add event listeners to buttons
document.getElementById("previous-button").addEventListener("click", handleButtonClick);
document.getElementById("next-button").addEventListener("click", handleButtonClick);
// Function to set the active pokemon based on the index
function setActivePokemon(divs,activeIndex) {
  for (var i = 0; i < divs.length; i++) {
    if (i === activeIndex) {
      divs[i].classList.remove("hidden");
    } else {divs[i].classList.add("hidden");}}
  localStorage.setItem("activeIndex", activeIndex);} // Store active index in memory
// Refresh party content every 5 seconds (5000 milliseconds)
async function main() {
  fetch("trackerdata.json").then((response) => response.json())
  .then((json) => refreshPartyContent(json))}
setInterval(main, 10000);
// Initially assign the "hidden" class to all Pokémon divs except the active one
for (var i = 0; i < pokemonDivs.length; i++) {
  if (i !== activeIndex) {pokemonDivs[i].classList.add("hidden");}}