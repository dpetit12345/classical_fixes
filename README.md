# classical_fixes
This Picard plugin helps solve numerous tagging issues common in classical music. It adds several plugin menus to the clustering pane at the cluster and file levels. It does not rely on MusicBrainz data. Rather it uses a local lookup file to normalize existing tags. It can be used before or after applying MusicBrainz data for cleanup purposes.
## Menus
The menus are:
1. Combine discs into a single album - this is useful for turning multi-disc sets (including boxed sets) that would normally span more than one album into a single album. After some validations to check that the selections belong to the same album, this makes all album names the same (stripping of "Disc 1," "Disc 2," etc.) and makes the album artist the same.
2. Do classical fixes on selected clusters - This performs numerous tag cleanup actions, using a local artist lookup table to embedded additional information:
    * Change word "No." in track title and album titles to use # instead. Common variations covered.
    * Change Opus to Op.
    * Performs several album title cleanup procedures.
    * When no composer is assigned, assign composer based on a common list of composers, extracting data from artists or album artists.
    * When no conductor is assigned, assign conductor based on a common list of conductors, extracting data from artists or album artists.
    * When no orchestra is assigned, assign orchestra based on a common list of orchestras, extracting data from artists or album artists.
    * Correct artist names against common misspellings.
    * Add composer sort tag, which is composer name sorted, LastName, FirstName.
    * Add composer view tag, which is composer name sorted, plus composers dates.
    * Standardize taxonomy by setting the epoque to primary epoque of the composer.
    * Normalize Album artist order by conductor, orchestra, followed by the rest of the original album artists.
    * Adds "Album Artist" tag to match "AlbumArtist" tag.
    * If there is no orchestra, but there is a artist of album artist name that looks like an orchestra, use that.
    * Remove composer from album artist and artist tags.
    * Remove "[conductorname]" from album titles.
3. Renumber tracks in albums sequentially - renumbers tracks in a multi-disc set so that it becomes one large single disc album. Original track and disc numbers are preserved in other tags. 
4. Do classical fixes on selected files - same as cluster version, only works at the individual file level
5. Renumber tracks sequentially by album - same as above, at the file level
6. Add Composer to Lookup - stores or updates the composer information in the lookup table. Composer View and Epoque tags must all be filled before the record can be updated.
7. Add Conductor to Lookup - stores or updates the conductor information in the lookup table.
8. Add Orchestra to Lookup - stores or updates the orchestra information in the lookup table.

