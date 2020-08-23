#include <fstream>
#include <iterator>

#include "NightfireModelFileReader.h"

#include "elements/HeaderV14.h"

namespace NFMDL
{
	NightfireModelFileReader::NightfireModelFileReader(const std::shared_ptr<NightfireModelFile>& modelFile) :
		m_ModelFile(modelFile)
	{
	}

	void NightfireModelFileReader::ReadFromFile(const std::string& filePath)
	{
		if ( !m_ModelFile )
		{
			throw std::runtime_error("ModelFile container was not set!");
		}

		std::ifstream input(filePath, std::ios::binary);

		if ( !input.good() )
		{
			throw std::runtime_error("Input file was not valid.");
		}

		m_InputFileData = std::make_unique<FileBuffer>(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());

		try
		{
			ReadEntireFile();
			m_InputFileData.reset();
		}
		catch ( const std::runtime_error& ex )
		{
			m_InputFileData.reset();
			throw ex;
		}

		catch ( const std::exception& ex )
		{
			m_InputFileData.reset();
			throw ex;
		}
	}

	void NightfireModelFileReader::ReadEntireFile()
	{
		ReadHeader();

		ReadElementArray(m_ModelFile->Header.bones, m_ModelFile->Bones);
		ReadElementArray(m_ModelFile->Header.boneControllers, m_ModelFile->BoneControllers);
		ReadElementArray(m_ModelFile->Header.hitBoxes, m_ModelFile->HitBoxes);
		ReadElementArray(m_ModelFile->Header.sequences, m_ModelFile->Sequences);
		ReadElementArray(m_ModelFile->Header.sequenceGroups, m_ModelFile->SequenceGroups);
		ReadElementArray(m_ModelFile->Header.textures, m_ModelFile->Textures);
		ReadElementArray(m_ModelFile->Header.attachments, m_ModelFile->Attachments);
		ReadElementArray(m_ModelFile->Header.soundGroups, m_ModelFile->SoundGroups);
	}

	void NightfireModelFileReader::ReadHeader()
	{
		m_ModelFile->Header = *GetElement<HeaderV14>();

		if ( m_ModelFile->Header.ident != HeaderIdentifier(FormatTraits<HeaderV14>::TARGET_IDENTIFIER) )
		{
			throw std::runtime_error("Input file header identifier did not match expected value.");
		}

		if ( m_ModelFile->Header.version != FormatTraits<HeaderV14>::TARGET_VERSION )
		{
			throw std::runtime_error("Input file header version " +
									 std::to_string(m_ModelFile->Header.version) +
									 "did not match expected version " +
									 std::to_string(FormatTraits<HeaderV14>::TARGET_VERSION) +
									 ".");
		}
	}
}