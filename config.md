
* `limitedToTheseDecks` Every sub section has a the ability to limit it to only certain deck names. Please note that the true deck name might differ from what's displayed visually. To get the correct deck name click the options/gear icon and click "rename" and copy the text. Both this and `globalDeckLimitation` support wildcards. For example `japanese*` will match `japanese kanji`,  `japanese sentences` etc.
* `globalDeckLimitation` This is for convenience if you just want all the features enabled but only for certain decks. This saves you having to enter the deck name in the `limitedToTheseDecks` for every option. 
    * Note: For a feature to be enabled the card must be apart of a deck in the `globalDeckLimitation` AND `limitedToTheseDecks` for that feature.  So if you have a global deck limit of `["Deck A"]` and the font randomizer has a deck limit of `["Deck B"]`, then Deck A will not have the font randomizer enabled, because the global deck limiter restricts that.

* `katakanaConverter` (Disabled by default) This feature swaps all hiragana and katakana around to allow for some extra katakana reading practice.
    *  `chance` Controls the percent chance to swap all hiragana and katakana. 
        * 0 is off, 1 is always swap, 0.5 is 50% chance. Any value between 0 and 1 works.
* `fontRandomizer` Switches randomly between a set of selected fonts
     * `fontsToRandomlyChoose` A list of what fonts to randomly change to. The fonts you enter in `fontsToRandomlyChoose`  **MUST** be in your `/collections.media` folder in anki. Format `["A.tff", "B.tff", "C.tcc"]`
     * NOTE: Do not include your default font in this. It will choose between the fonts in this list AND the one you have on your card already. For example if you want to choose from fonts `A.tff`, `B.tff`, and `C.tff`, and the font on your card is already `A.tff` then `fontsToRandomlyChoose` should be `["B.tff", "C.tff"]`
    * A few fonts are included by default
 
 * `verticalText` Switches the card to layout text in a vertical left to right fashion, just like light novels are displayed. This is for vertical text reading practice
    * `chance` The chance to convert to vertical text. NOTE: This is set to `0` by default.
    * NOTE: This feature requires you to mark what section of your card is your expression field by adding the class name `expression-field` to it. Also for ease of use, Migaku cards should work by default as the class name `migaku-word-front` is also used to enable this feature. For example, if you edit your card and see something like `<div class="question">{{Expression}}</div>` you just need to add `expression-field` to the class list like so `<div class="question expression-field">{{Expression}}</div>`
    * This feature may mess with your layout in unexpected ways (although it's only temporary). If you run into issues after turning it on, set it back to 0 and let me know what went wrong through a github issue https://github.com/Toocanzs/AnkiJapaneseCardRandomizer/issues/new
    * `styleMaxHeight` This controls the maximum height for vertical text. Default is 80% of the screen size.

* `sizeRandomizer` Randomizes size of any elements with `expression-field` or `migaku-word-front` as their class. To set this up read the setup instructions for `verticalText`
    * `enabled` Enables the feature. `true` or `false`
    * `minSize` Minimum size
    * `maxSize` Maximum size
    * `units` Sets the units to use for styling the font size. For example `px` as a unit would mean that if 50 was randomly chosen to be the font size, the final style would be `50px`


