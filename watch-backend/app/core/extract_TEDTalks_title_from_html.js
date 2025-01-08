// A javascript script to retrieve the titles of videos from TED Talks' website.

// Define a function to extract titles dynamically
function getAllTitles() {
    // Base XPath to match all title spans dynamically
    const baseXPath = '/html/body/div[1]/div[2]/main/div[2]/div[2]/section/div/div[2]/div/div/a/div/div/div[2]/div[1]/div/span';

    // Use XPath to select all matching elements
    let elements = document.evaluate(
        baseXPath,
        document,
        null,
        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
        null
    );

    // Extract the text content from each matching element
    let titles = [];
    for (let i = 0; i < elements.snapshotLength; i++) {
        titles.push(elements.snapshotItem(i).textContent.trim());
    }

    return titles;
}

// Get all titles
let titles = getAllTitles();

// Print the titles to the console
console.log(titles);

// Optionally, copy the titles to the clipboard
copy(titles.join('\n'));

// Output the titles as an array
titles;


let blob = new Blob([titles.join('\n')], {type: 'text/plain'});
let a = document.createElement('a');
a.href = URL.createObjectURL(blob);
a.download = 'ted_titles.txt';
a.click();
